# Graph Report - .  (2026-07-28)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 324 nodes · 480 edges · 36 communities (31 shown, 5 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 43 edges (avg confidence: 0.69)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `388d3761`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- jquery-1.10.2.min.js
- views.py
- .tip
- jquery-1.10.2.js
- modernizr-2.6.2.js
- benchmark_lfw.py
- .slide
- jquery.validate.unobtrusive.js
- matcherFromTokens
- Animation
- ArgosFormatter
- defaultPrefilter
- setMatcher
- bootstrap.min.js
- fixCloneNodeIssues
- internalRemoveData
- deploy.sh
- deploy-production.sh

## God Nodes (most connected - your core abstractions)
1. `wt()` - 11 edges
2. `at()` - 10 edges
3. `log_response()` - 9 edges
4. `i()` - 9 edges
5. `log_error()` - 8 edges
6. `s()` - 8 edges
7. `log_model_operation()` - 7 edges
8. `createElement()` - 7 edges
9. `identify_face()` - 7 edges
10. `api_route()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `winnow()` --indirect_call--> `i()`  [INFERRED]
  ARGOS/static/scripts/jquery-1.10.2.js → ARGOS/static/scripts/jquery.validate.unobtrusive.min.js
- `done()` --indirect_call--> `s()`  [INFERRED]
  ARGOS/static/scripts/jquery-1.10.2.js → ARGOS/static/scripts/jquery.validate.min.js
- `ft()` --indirect_call--> `t()`  [INFERRED]
  ARGOS/static/scripts/jquery-1.10.2.min.js → ARGOS/static/scripts/respond.min.js
- `wt()` --indirect_call--> `g()`  [INFERRED]
  ARGOS/static/scripts/jquery-1.10.2.min.js → ARGOS/static/scripts/jquery.validate.unobtrusive.min.js
- `Hn()` --indirect_call--> `n()`  [INFERRED]
  ARGOS/static/scripts/jquery-1.10.2.min.js → ARGOS/static/scripts/jquery.validate.unobtrusive.min.js

## Import Cycles
- None detected.

## Communities (36 total, 5 thin omitted)

### Community 0 - "jquery-1.10.2.min.js"
Cohesion: 0.05
Nodes (44): an(), at(), bt(), ct(), er(), ft(), Hn(), ht() (+36 more)

### Community 1 - "views.py"
Cohesion: 0.06
Nodes (43): Any, IcarusApiClient, IcarusApiUnavailableError, Exception, ARGOS - API Client for ICARUS.API Handles communication with the .NET backend f, Backend no disponible (timeout, conexion rechazada, o 5xx tras agotar reintentos, Client for communicating with ICARUS.API, Get all facial embeddings for a client          Args:             cliente_id: (+35 more)

### Community 2 - ".tip"
Cohesion: 0.07
Nodes (3): clearMenus(), getParent(), NOTE: POPOVER EXTENDS tooltip.js

### Community 3 - "jquery-1.10.2.js"
Cohesion: 0.06
Nodes (3): augmentWidthOrHeight(), getWidthOrHeight(), NOTE: we've included the "window" in window.getComputedStyle

### Community 4 - "modernizr-2.6.2.js"
Cohesion: 0.24
Nodes (16): addStyleSheet(), contains(), createDocumentFragment(), createElement(), getElements(), getExpandoData(), is(), isEventSupported() (+8 more)

### Community 5 - "benchmark_lfw.py"
Cohesion: 0.22
Nodes (14): compare_embeddings(), extract_embedding(), get_persons_with_multiple_photos(), image_to_base64(), main(), ARGOS Benchmark Script - LFW Dataset Testing Tests facial recognition accuracy, Test 2: Different person verification (should NOT match)     Compare person1.ph, Find persons with at least min_photos images (+6 more)

### Community 7 - "jquery.validate.unobtrusive.js"
Cohesion: 0.27
Nodes (6): escapeAttributeValue(), onError(), onErrors(), onReset(), onSuccess(), validationInfo()

### Community 8 - "matcherFromTokens"
Cohesion: 0.38
Nodes (7): addCombinator(), elementMatcher(), matcherFromTokens(), select(), Sizzle(), tokenize(), toSelector()

### Community 9 - "Animation"
Cohesion: 0.29
Nodes (7): ajaxConvert(), ajaxHandleResponses(), Animation(), createFxNow(), done(), propFilter(), Tween()

### Community 10 - "ArgosFormatter"
Cohesion: 0.33
Nodes (5): ArgosFormatter, Custom formatter for ARGOS logs, Configure and return the ARGOS logger.     Log file is cleared on each startup, setup_logger(), Logger

### Community 11 - "defaultPrefilter"
Cohesion: 0.40
Nodes (6): actualDisplay(), createTween(), css_defaultDisplay(), defaultPrefilter(), isHidden(), showHide()

### Community 12 - "setMatcher"
Cohesion: 0.40
Nodes (6): condense(), createPositionalPseudo(), markFunction(), matcherFromGroupMatchers(), multipleContexts(), setMatcher()

### Community 16 - "fixCloneNodeIssues"
Cohesion: 0.67
Nodes (3): disableScript(), fixCloneNodeIssues(), restoreScript()

## Knowledge Gaps
- **2 isolated node(s):** `deploy-production.sh script`, `deploy.sh script`
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `s()` connect `jquery-1.10.2.min.js` to `Animation`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `done()` connect `Animation` to `defaultPrefilter`, `jquery-1.10.2.min.js`, `jquery-1.10.2.js`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `wt()` (e.g. with `s()` and `f()`) actually correct?**
  _`wt()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `at()` (e.g. with `s()` and `i()`) actually correct?**
  _`at()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `i()` (e.g. with `at()` and `vt()`) actually correct?**
  _`i()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `deploy-production.sh script`, `deploy.sh script` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `jquery-1.10.2.min.js` be split into smaller, more focused modules?**
  _Cohesion score 0.05328218243819267 - nodes in this community are weakly interconnected._