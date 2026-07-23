# Troubleshooting & Maintenance

<cite>
**Referenced Files in This Document**
- [backend/main.py](file://backend/main.py)
- [auth/auth_manager.py](file://auth/auth_manager.py)
- [reliability/monitoring.py](file://reliability/monitoring.py)
- [reliability/graceful_degradation.py](file://reliability/graceful_degradation.py)
- [reliability/retry_strategy.py](file://reliability/retry_strategy.py)
- [services/rag-service/main.py](file://services/rag-service/main.py)
- [config.py](file://config.py)
- [rebuild_vectorstore.py](file://rebuild_vectorstore.py)
- [docker-compose.production.yml](file://docker-compose.production.yml)
- [requirements.txt](file://requirements.txt)
- [security/security_logger.py](file://security/security_logger.py)
- [educational_engine/cache_manager.py](file://educational_engine/cache_manager.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Maintenance Procedures](#maintenance-procedures)
10. [Conclusion](#conclusion)

## Introduction
This document provides comprehensive troubleshooting and maintenance guidance for MinerAI. It covers common operational issues, diagnostics, monitoring, debugging, and maintenance workflows across the backend, authentication, vector database, and distributed services. It also includes practical steps for connection problems, performance tuning, authentication failures, vector database errors, system updates, backups, and disaster recovery.

## Project Structure
MinerAI is a modular FastAPI-based system with a distributed microservices architecture. Key areas include:
- Backend API gateway and core services
- Authentication and user management
- Reliability subsystems (monitoring, graceful degradation, retry)
- Educational engine caching
- Vector database management and rebuilding
- Production deployment via Docker Compose

```mermaid
graph TB
subgraph "API Gateway"
A["FastAPI App<br/>backend/main.py"]
end
subgraph "Services"
B["RAG Service<br/>services/rag-service/main.py"]
C["Auth Service<br/>auth/auth_manager.py"]
end
subgraph "Reliability"
D["Monitoring<br/>reliability/monitoring.py"]
E["Graceful Degradation<br/>reliability/graceful_degradation.py"]
F["Retry Strategy<br/>reliability/retry_strategy.py"]
end
subgraph "Caching"
G["Educational Cache<br/>educational_engine/cache_manager.py"]
end
subgraph "Vector DB"
H["Rebuild Script<br/>rebuild_vectorstore.py"]
I["Config<br/>config.py"]
end
A --> B
A --> C
B --> D
B --> E
B --> F
B --> G
B --> H
B --> I
```

**Diagram sources**
- [backend/main.py:1-69](file://backend/main.py#L1-L69)
- [services/rag-service/main.py:1-299](file://services/rag-service/main.py#L1-L299)
- [auth/auth_manager.py:1-393](file://auth/auth_manager.py#L1-L393)
- [reliability/monitoring.py:1-373](file://reliability/monitoring.py#L1-L373)
- [reliability/graceful_degradation.py:1-329](file://reliability/graceful_degradation.py#L1-L329)
- [reliability/retry_strategy.py:1-303](file://reliability/retry_strategy.py#L1-L303)
- [educational_engine/cache_manager.py:1-327](file://educational_engine/cache_manager.py#L1-L327)
- [rebuild_vectorstore.py:1-55](file://rebuild_vectorstore.py#L1-L55)
- [config.py:1-218](file://config.py#L1-L218)

**Section sources**
- [backend/main.py:1-69](file://backend/main.py#L1-L69)
- [services/rag-service/main.py:1-299](file://services/rag-service/main.py#L1-L299)
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)

## Core Components
- Backend API entrypoint initializes FastAPI, CORS, and routes, and exposes health checks.
- RAG Service orchestrates the pipeline, integrates Redis, external services, and Celery workers.
- Auth Manager supports JWT-based authentication with MongoDB or JSON fallback.
- Monitoring tracks request traces, aggregates metrics, and raises alerts.
- Graceful Degradation manages service modes and fallback responses.
- Retry Strategy implements exponential backoff and adaptive retry.
- Educational Cache Manager provides multi-layer caching for responses and teaching elements.
- Vector DB rebuild script automates safe rebuilding of ChromaDB with backup and rename strategies.
- Config centralizes paths, API keys, model settings, performance toggles, logging, and validation.

**Section sources**
- [backend/main.py:11-69](file://backend/main.py#L11-L69)
- [services/rag-service/main.py:31-299](file://services/rag-service/main.py#L31-L299)
- [auth/auth_manager.py:58-393](file://auth/auth_manager.py#L58-L393)
- [reliability/monitoring.py:261-373](file://reliability/monitoring.py#L261-L373)
- [reliability/graceful_degradation.py:74-329](file://reliability/graceful_degradation.py#L74-L329)
- [reliability/retry_strategy.py:86-303](file://reliability/retry_strategy.py#L86-L303)
- [educational_engine/cache_manager.py:31-327](file://educational_engine/cache_manager.py#L31-L327)
- [rebuild_vectorstore.py:1-55](file://rebuild_vectorstore.py#L1-L55)
- [config.py:138-218](file://config.py#L138-L218)

## Architecture Overview
The system runs as a multi-container Docker Compose stack with Nginx as the load balancer, a FastAPI gateway, microservices for RAG, embedding, retrieval, reranking, translation, and authentication, Redis for caching and Celery workers for async tasks, and MongoDB for persistence.

```mermaid
graph TB
LB["Nginx Load Balancer"]
GW["API Gateway (FastAPI)"]
FE["Frontend"]
RS["RAG Service"]
ES["Embedding Service"]
RTS["Retrieval Service"]
RRS["Reranking Service"]
TS["Translation Service"]
AS["Auth Service"]
CW["Celery Worker"]
CB["Celery Beat"]
R["Redis"]
M["MongoDB"]
LB --> FE
LB --> GW
GW --> RS
GW --> AS
RS --> ES
RS --> RTS
RS --> RRS
RS --> TS
RS --> R
RS --> M
AS --> M
CW --> R
CB --> R
CW --> M
RTS --> M
```

**Diagram sources**
- [docker-compose.production.yml:7-359](file://docker-compose.production.yml#L7-L359)

**Section sources**
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)

## Detailed Component Analysis

### Monitoring and Alerting
The monitoring system records request traces, aggregates performance metrics, and triggers alerts for high error rates, slow requests, and quota usage. It exposes a dashboard summarizing uptime, recent traces, slow requests, and active alerts.

```mermaid
classDiagram
class RequestTrace {
+string request_id
+string endpoint
+float start_time
+float end_time
+float duration
+string status
+string error
+dict metadata
}
class PerformanceMetrics {
+int total_requests
+int successful_requests
+int failed_requests
+float total_duration
+float min_duration
+float max_duration
+get_avg_duration() float
+get_success_rate() float
}
class RequestTracer {
+deque traces
+dict active_traces
+start_trace(request_id, endpoint, **metadata) RequestTrace
+end_trace(request_id, success, error) void
+get_recent_traces(limit) RequestTrace[]
+get_slow_requests(threshold) RequestTrace[]
}
class MetricsCollector {
+dict metrics_by_endpoint
+dict metrics_by_service
+dict error_counts
+dict quota_usage
+record_request(endpoint, service, duration, success, error) void
+record_quota_usage(service, used, limit) void
+get_summary() Dict
}
class AlertManager {
+Dict[] alerts
+dict alert_thresholds
+check_error_rate(metrics) void
+check_slow_requests(traces) void
+check_quota_usage(quota_data) void
+create_alert(alert_type, message, severity) void
+get_active_alerts(since_minutes) Dict[]
}
class MonitoringSystem {
+RequestTracer tracer
+MetricsCollector metrics
+AlertManager alerts
+datetime start_time
+start_request(request_id, endpoint, **metadata) RequestTrace
+end_request(request_id, endpoint, service, success, error) void
+record_quota(service, used, limit) void
+run_health_check() void
+get_dashboard() Dict
}
MonitoringSystem --> RequestTracer : "uses"
MonitoringSystem --> MetricsCollector : "uses"
MonitoringSystem --> AlertManager : "uses"
```

**Diagram sources**
- [reliability/monitoring.py:22-373](file://reliability/monitoring.py#L22-L373)

**Section sources**
- [reliability/monitoring.py:261-373](file://reliability/monitoring.py#L261-L373)

### Graceful Degradation and Fallbacks
Graceful Degradation monitors service health and transitions between FULL, DEGRADED, MINIMAL, and OFFLINE modes. It provides fallback responses and timeout-handling strategies to maintain availability under failure conditions.

```mermaid
flowchart TD
Start(["Call Service"]) --> CheckMode["Check Service Mode"]
CheckMode --> Offline{"OFFLINE?"}
Offline --> |Yes| Fallback["Use Fallback Function"]
Offline --> |No| TryPrimary["Try Primary Function"]
TryPrimary --> Success{"Success?"}
Success --> |Yes| RecordSuccess["Record Success"]
Success --> |No| RecordError["Record Error"]
RecordError --> Transition["Transition Mode Based on Error Count"]
Transition --> FallbackCheck{"Fallback Available?"}
FallbackCheck --> |Yes| TryFallback["Try Fallback"]
FallbackCheck --> |No| RaiseError["Raise Original Error"]
TryFallback --> FallbackSuccess{"Fallback Success?"}
FallbackSuccess --> |Yes| ReturnFallback["Return Fallback Result"]
FallbackSuccess --> |No| RaiseError
RecordSuccess --> ReturnResult["Return Result"]
```

**Diagram sources**
- [reliability/graceful_degradation.py:158-209](file://reliability/graceful_degradation.py#L158-L209)

**Section sources**
- [reliability/graceful_degradation.py:74-329](file://reliability/graceful_degradation.py#L74-L329)

### Retry Strategy with Exponential Backoff
The retry system implements exponential backoff with jitter, retry budgets, and adaptive retry logic to prevent retry storms and improve resilience.

```mermaid
flowchart TD
CallFunc["Call Function"] --> Attempt["Attempt"]
Attempt --> Success{"Success?"}
Success --> |Yes| LogSuccess["Log Success"] --> Return["Return Result"]
Success --> |No| CheckBudget{"Retry Budget OK?"}
CheckBudget --> |No| FailFast["Fail Fast"] --> Raise["Raise Last Exception"]
CheckBudget --> |Yes| CalcDelay["Calculate Delay (Exp Backoff + Jitter)"]
CalcDelay --> Sleep["Sleep Delay"]
Sleep --> Attempt
```

**Diagram sources**
- [reliability/retry_strategy.py:86-194](file://reliability/retry_strategy.py#L86-L194)

**Section sources**
- [reliability/retry_strategy.py:20-303](file://reliability/retry_strategy.py#L20-L303)

### Authentication and Security Logging
Authentication uses JWT with optional MongoDB-backed user storage and JSON fallback. Security logging captures security events, suspicious activity detection, and audit trails.

```mermaid
sequenceDiagram
participant Client as "Client"
participant AuthSvc as "Auth Service"
participant Mongo as "MongoDB"
participant SecLog as "Security Logger"
Client->>AuthSvc : POST /login {email, password}
AuthSvc->>Mongo : Find user by email
Mongo-->>AuthSvc : User document
AuthSvc->>AuthSvc : Verify password
AuthSvc->>SecLog : log_login_success/log_login_failed
AuthSvc-->>Client : {token, user_info}
```

**Diagram sources**
- [auth/auth_manager.py:174-218](file://auth/auth_manager.py#L174-L218)
- [security/security_logger.py:138-156](file://security/security_logger.py#L138-L156)

**Section sources**
- [auth/auth_manager.py:58-393](file://auth/auth_manager.py#L58-L393)
- [security/security_logger.py:39-395](file://security/security_logger.py#L39-L395)

### Educational Cache Manager
The cache manager implements a four-layer cache: query responses, knowledge base, embeddings, and fragments, with Redis and in-memory layers and TTL policies.

```mermaid
classDiagram
class CacheManager {
-Redis redis_client
+Dict TTL
+Dict memory_cache
+Dict knowledge_base
+get_cached_response(question, user_id) Dict
+cache_response(question, response, user_id) void
+get_teaching_element(concept, element_type) string
+cache_teaching_element(concept, element_type, content) void
+cache_embedding(document_id, embedding) void
+get_embedding(document_id) float[]
+get_cache_stats() Dict
+clear_cache(pattern) int
+close() void
}
```

**Diagram sources**
- [educational_engine/cache_manager.py:31-327](file://educational_engine/cache_manager.py#L31-L327)

**Section sources**
- [educational_engine/cache_manager.py:31-327](file://educational_engine/cache_manager.py#L31-L327)

### Vector Database Rebuild Workflow
The rebuild script safely backs up the target directory, deletes it, and rebuilds the vector store from loaded documents, ensuring minimal downtime and recoverability.

```mermaid
flowchart TD
Start(["Start Rebuild"]) --> Force{"--force flag?"}
Force --> |No| Prompt["Prompt user confirmation"]
Prompt --> Confirm{"User confirms?"}
Confirm --> |No| Exit["Exit"]
Confirm --> |Yes| Proceed["Proceed"]
Force --> |Yes| Proceed
Proceed --> Backup["Backup Target Directory"]
Backup --> Delete["Delete Target Directory"]
Delete --> Load["Load Documents from data/"]
Load --> Create["Create Vector Store"]
Create --> Done(["Done"])
```

**Diagram sources**
- [rebuild_vectorstore.py:46-55](file://rebuild_vectorstore.py#L46-L55)

**Section sources**
- [rebuild_vectorstore.py:1-55](file://rebuild_vectorstore.py#L1-L55)

## Dependency Analysis
External dependencies include LangChain, ChromaDB, sentence-transformers, Redis, MongoDB, and Google Generative AI. These are declared in requirements and used across services and components.

```mermaid
graph TB
Req["requirements.txt"]
LC["langchain*"]
CH["chromadb"]
ST["sentence-transformers"]
RD["redis"]
PM["pymongo"]
GA["google-generativeai"]
Req --> LC
Req --> CH
Req --> ST
Req --> RD
Req --> PM
Req --> GA
```

**Diagram sources**
- [requirements.txt:1-43](file://requirements.txt#L1-L43)

**Section sources**
- [requirements.txt:1-43](file://requirements.txt#L1-L43)

## Performance Considerations
- Enable and tune caches: embedding, BM25, vector DB, and educational cache.
- Adjust concurrency and batch sizes for embedding and vector DB operations.
- Use Redis for query response caching and reduce LLM calls.
- Monitor slow requests and error rates via the monitoring system.
- Apply graceful degradation and fallbacks to maintain responsiveness under load.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide

### Connection Problems
Symptoms:
- Services unreachable or health checks failing.
- Redis/MongoDB connectivity errors.
- Cross-service communication timeouts.

Common causes and fixes:
- Verify service endpoints and environment variables in compose.
- Check Redis and MongoDB health checks and container logs.
- Ensure proper network configuration and port mappings.
- Validate API keys and service URLs in the RAG service.

**Section sources**
- [docker-compose.production.yml:61-66](file://docker-compose.production.yml#L61-L66)
- [docker-compose.production.yml:276-281](file://docker-compose.production.yml#L276-L281)
- [services/rag-service/main.py:21-44](file://services/rag-service/main.py#L21-L44)

### Authentication Failures
Symptoms:
- Login failures, expired tokens, or unauthorized access.
- Missing JWT secret or invalid configuration.

Common causes and fixes:
- Set JWT_SECRET_KEY in environment variables.
- Verify MongoDB URI and collection indices.
- Check password hashing and token verification logic.
- Review security logs for suspicious activity.

**Section sources**
- [auth/auth_manager.py:21-34](file://auth/auth_manager.py#L21-L34)
- [auth/auth_manager.py:62-87](file://auth/auth_manager.py#L62-L87)
- [security/security_logger.py:138-250](file://security/security_logger.py#L138-L250)

### Performance Issues
Symptoms:
- Slow response times, high error rates, or quota exhaustion.

Common causes and fixes:
- Enable and monitor caching layers (Redis, educational cache).
- Tune chunking, hybrid search weights, and reranking thresholds.
- Use monitoring dashboards to identify slow endpoints and traces.
- Apply graceful degradation and retry strategies.

**Section sources**
- [config.py:99-111](file://config.py#L99-L111)
- [config.py:138-160](file://config.py#L138-L160)
- [reliability/monitoring.py:309-328](file://reliability/monitoring.py#L309-L328)
- [reliability/graceful_degradation.py:158-209](file://reliability/graceful_degradation.py#L158-L209)
- [reliability/retry_strategy.py:86-194](file://reliability/retry_strategy.py#L86-L194)

### Vector Database Errors
Symptoms:
- ChromaDB persistence errors, permission issues, or rebuild failures.

Common causes and fixes:
- Run the rebuild script with backup and safe deletion.
- Ensure write permissions for the target directory.
- Validate embedding model and chunking settings.
- Check service health and logs for persistent failures.

**Section sources**
- [rebuild_vectorstore.py:12-32](file://rebuild_vectorstore.py#L12-L32)
- [config.py:138-160](file://config.py#L138-L160)

### Debugging Techniques
- Use monitoring dashboards to inspect recent traces and slow requests.
- Inspect security logs for authentication and access events.
- Enable detailed logging via configuration and review log files.
- Leverage graceful degradation fallbacks to isolate failing components.

**Section sources**
- [reliability/monitoring.py:309-328](file://reliability/monitoring.py#L309-L328)
- [security/security_logger.py:64-93](file://security/security_logger.py#L64-L93)
- [config.py:122-128](file://config.py#L122-L128)

## Maintenance Procedures

### System Updates
- Update dependencies via requirements and rebuild containers.
- Validate configuration changes and run health checks.
- Restart services in order: Redis, MongoDB, then API gateway and services.

**Section sources**
- [requirements.txt:1-43](file://requirements.txt#L1-L43)
- [docker-compose.production.yml:61-66](file://docker-compose.production.yml#L61-L66)

### Backup Procedures
- Backup ChromaDB directories before rebuilds.
- Maintain MongoDB backups according to your retention policy.
- Keep security logs rotated and retained per policy.

**Section sources**
- [rebuild_vectorstore.py:12-18](file://rebuild_vectorstore.py#L12-L18)
- [docker-compose.production.yml:284-359](file://docker-compose.production.yml#L284-L359)
- [security/security_logger.py:72-92](file://security/security_logger.py#L72-L92)

### Disaster Recovery
- Restore from latest backups and redeploy compose stack.
- Validate service health checks and connectivity.
- Gradually restore traffic and monitor metrics.

**Section sources**
- [docker-compose.production.yml:61-66](file://docker-compose.production.yml#L61-L66)
- [docker-compose.production.yml:276-281](file://docker-compose.production.yml#L276-L281)

### Diagnostic Tools and Logging
- Monitoring dashboard for uptime, metrics, recent traces, slow requests, and alerts.
- Security logger for audit trails and suspicious activity detection.
- Application logs configured with rotation and file paths.

**Section sources**
- [reliability/monitoring.py:309-328](file://reliability/monitoring.py#L309-L328)
- [security/security_logger.py:64-93](file://security/security_logger.py#L64-L93)
- [config.py:122-128](file://config.py#L122-L128)

### Performance Optimization Techniques
- Enable caching layers and adjust TTLs.
- Tune chunking and hybrid search weights.
- Use adaptive retry and graceful degradation.
- Monitor and scale Redis and MongoDB capacity.

**Section sources**
- [educational_engine/cache_manager.py:53-59](file://educational_engine/cache_manager.py#L53-L59)
- [config.py:67-87](file://config.py#L67-L87)
- [reliability/retry_strategy.py:197-240](file://reliability/retry_strategy.py#L197-L240)
- [reliability/graceful_degradation.py:18-24](file://reliability/graceful_degradation.py#L18-L24)

## Conclusion
This guide consolidates MinerAI’s operational and maintenance practices. By leveraging monitoring, graceful degradation, retry strategies, robust logging, and structured maintenance workflows—especially around vector database rebuilds—you can sustain reliable performance, quickly diagnose issues, and recover from incidents efficiently.