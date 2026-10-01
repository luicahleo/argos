#!/usr/bin/env bash
# Deploy ARGOS to the production VPS after an isolated candidate smoke check.

set -euo pipefail

DEPLOY_USER="root"
DEPLOY_HOST="194.164.171.217"
REMOTE_PATH="/var/apps/icarus/microservicios/argos"

echo "Deploying ARGOS candidate to production..."
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "mkdir -p '${REMOTE_PATH}/logs'"
rsync -az \
    --exclude='env/' \
    --exclude='env_new/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='.env.production' \
    --exclude='logs/*.log' \
    ./ "${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_PATH}/"

ssh "${DEPLOY_USER}@${DEPLOY_HOST}" 'bash -s' <<'ENDSSH'
set -Eeuo pipefail
cd /var/apps/icarus/microservicios/argos

readonly CANDIDATE_CONTAINER="argos-v2-candidate"
readonly PREVIOUS_IMAGE="argos:previous"
readonly CANDIDATE_IMAGE="argos:control-acceso-validacion"
readonly NETWORK="trajano-shared-network"
readonly ENV_FILE=".env.production"
readonly LOG_DIR="$(pwd)/logs"
SWAP_STARTED=0

rollback_on_error() {
    local exit_code="${1:-$?}"
    trap - ERR
    set +e

    docker rm -f "$CANDIDATE_CONTAINER" >/dev/null 2>&1

    if [[ "$SWAP_STARTED" == "1" ]]; then
        echo "Candidate swap failed; restoring the previous ARGOS container."
        docker rm -f argos >/dev/null 2>&1
        if docker image inspect "$PREVIOUS_IMAGE" >/dev/null 2>&1; then
            docker run -d \
                --name argos \
                --network "$NETWORK" \
                --restart unless-stopped \
                --memory 2g \
                --log-driver json-file \
                --log-opt max-size=10m \
                --log-opt max-file=5 \
                --env-file "$ENV_FILE" \
                -v "$LOG_DIR:/app/logs" \
                "$PREVIOUS_IMAGE" >/dev/null
        fi
    fi

    exit "$exit_code"
}
trap rollback_on_error ERR
trap 'rollback_on_error 130' INT
trap 'rollback_on_error 143' TERM

if [[ ! -r "$ENV_FILE" ]] || ! grep -q '^CONTROL_ACCESO_API_KEY=.' "$ENV_FILE"; then
    echo "Production environment file or required API key is unavailable."
    exit 1
fi
if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
    echo "Required shared Docker network is unavailable."
    exit 1
fi

docker build -f Dockerfile -t "$CANDIDATE_IMAGE" .
if docker image inspect argos:latest >/dev/null 2>&1; then
    docker tag argos:latest "$PREVIOUS_IMAGE"
fi

docker rm -f "$CANDIDATE_CONTAINER" >/dev/null 2>&1 || true
docker run -d \
    --name "$CANDIDATE_CONTAINER" \
    --network "$NETWORK" \
    --restart unless-stopped \
    --memory 2g \
    --log-driver json-file \
    --log-opt max-size=10m \
    --log-opt max-file=5 \
    --env-file "$ENV_FILE" \
    -v "$LOG_DIR:/app/logs" \
    "$CANDIDATE_IMAGE" >/dev/null

echo "Waiting for candidate health and authenticated contract routes..."
for attempt in $(seq 1 24); do
    if docker exec "$CANDIDATE_CONTAINER" curl -fsS \
        http://127.0.0.1:5000/health >/dev/null 2>&1; then
        break
    fi
    if [[ "$attempt" == "24" ]]; then
        echo "Candidate health check failed."
        rollback_on_error 1
    fi
    sleep 5
done

candidate_status() {
    local method="$1"
    local route="$2"
    local expected="$3"
    local actual

    actual=$(docker exec "$CANDIDATE_CONTAINER" sh -c \
        'curl -sS -o /dev/null -w "%{http_code}" -X "$1" -H "Authorization: Bearer $CONTROL_ACCESO_API_KEY" "http://127.0.0.1:5000$2"' \
        sh "$method" "$route")
    if [[ "$actual" != "$expected" ]]; then
        echo "Candidate authenticated route smoke check failed: $route (HTTP $actual)."
        return 1
    fi
}

candidate_status POST /api/verify 400
candidate_status GET /api/v2/control-acceso/capacidades 200
candidate_status POST /api/v2/control-acceso/extracciones 400
candidate_status POST /api/v2/control-acceso/identificaciones 400

# The candidate is healthy and the authenticated v2 routes responded as expected.
# Only now stop the old container and assign the production tag.
SWAP_STARTED=1
if docker container inspect argos >/dev/null 2>&1; then
    docker stop argos >/dev/null
    docker rm argos >/dev/null
fi
docker rename "$CANDIDATE_CONTAINER" argos
docker tag "$CANDIDATE_IMAGE" argos:latest

for attempt in $(seq 1 12); do
    if docker exec argos curl -fsS http://127.0.0.1:5000/health >/dev/null 2>&1; then
        break
    fi
    if [[ "$attempt" == "12" ]]; then
        echo "Production container health check failed after swap."
        rollback_on_error 1
    fi
    sleep 5
done

trap - ERR INT TERM
echo "ARGOS candidate passed smoke checks and is now running as production."
ENDSSH
