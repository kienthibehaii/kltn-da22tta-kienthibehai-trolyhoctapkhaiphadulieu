# Backend Architecture

<cite>
**Referenced Files in This Document**
- [backend/main.py](file://backend/main.py)
- [services/api-gateway/main.py](file://services/api-gateway/main.py)
- [services/rag-service/main.py](file://services/rag-service/main.py)
- [services/embedding-service/main.py](file://services/embedding-service/main.py)
- [services/retrieval-service/main.py](file://services/retrieval-service/main.py)
- [auth/auth_manager.py](file://auth/auth_manager.py)
- [auth/api_routes.py](file://auth/api_routes.py)
- [advanced_rag/pipeline/integrated_rag.py](file://advanced_rag/pipeline/integrated_rag.py)
- [docker-compose.production.yml](file://docker-compose.production.yml)
- [requirements.txt](file://requirements.txt)
- [enterprise/src/core/config.py](file://enterprise/src/core/config.py)
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
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document describes the backend architecture of the MinerAI system, a FastAPI-based microservices platform integrating Retrieval-Augmented Generation (RAG). It covers the API gateway implementation, microservices design pattern, layered architecture, component interactions, data flows, authentication system, and service coordination mechanisms. It also outlines infrastructure requirements, scalability considerations, and deployment topology, including integrations with Google Gemini API and ChromaDB.

## Project Structure
The backend follows a modular FastAPI architecture with a dedicated API gateway and multiple specialized microservices:
- API Gateway: Centralized ingress handling routing, authentication, rate limiting, and observability.
- RAG Service: Orchestrates the RAG pipeline, integrates with retrieval, reranking, translation, and LLMs.
- Retrieval Service: Provides vector and keyword search with hybrid fusion and caching.
- Embedding Service: Generates and caches embeddings with batching and GPU support.
- Auth Module: Manages user registration, login, JWT tokens, and chat history.
- Advanced RAG Pipeline: A production-ready pipeline combining ingestion, retrieval, reranking, generation, memory, and evaluation.
- Infrastructure: Docker Compose defines the production topology with Nginx, Redis, MongoDB, and monitoring stacks.

```mermaid
graph TB
subgraph "External Clients"
FE["Frontend"]
Admin["Admin Tools"]
end
subgraph "API Gateway Layer"
GW["API Gateway"]
end
subgraph "Microservices"
RS["RAG Service"]
RET["Retrieval Service"]
EMB["Embedding Service"]
AUTH["Auth Service"]
RER["Reranking Service"]
TR["Translation Service"]
end
subgraph "Infrastructure"
REDIS["Redis"]
MONGO["MongoDB"]
NGINX["Nginx"]
PROM["Prometheus"]
GF["Grafana"]
end
FE --> NGINX
Admin --> NGINX
NGINX --> GW
GW --> RS
GW --> AUTH
RS --> RET
RS --> RER
RS --> TR
RS --> REDIS
RS --> MONGO
RET --> REDIS
RET --> MONGO
EMB --> REDIS
AUTH --> MONGO
RER --> REDIS
TR --> REDIS
GW --> REDIS
GW --> PROM
PROM --> GF
```

**Diagram sources**
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)
- [services/api-gateway/main.py:1-269](file://services/api-gateway/main.py#L1-L269)
- [services/rag-service/main.py:1-299](file://services/rag-service/main.py#L1-L299)
- [services/retrieval-service/main.py:1-275](file://services/retrieval-service/main.py#L1-L275)
- [services/embedding-service/main.py:1-204](file://services/embedding-service/main.py#L1-L204)
- [auth/api_routes.py:1-352](file://auth/api_routes.py#L1-L352)

**Section sources**
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)
- [backend/main.py:1-69](file://backend/main.py#L1-L69)

## Core Components
- API Gateway: Handles CORS, rate limiting, JWT verification via Auth Service, Prometheus metrics, and proxies requests to downstream services.
- RAG Service: Orchestrates the RAG pipeline, performs caching, translates queries and answers, and coordinates with Retrieval, Reranking, and Translation services.
- Retrieval Service: Implements vector search, BM25 keyword search, reciprocal rank fusion (RRF), and caching.
- Embedding Service: Encodes texts into vectors with caching, batching, and optional GPU acceleration.
- Auth Module: Provides user management, JWT lifecycle, and chat history APIs.
- Advanced RAG Pipeline: A comprehensive pipeline integrating ingestion, retrieval, reranking, generation, memory, and evaluation.

**Section sources**
- [services/api-gateway/main.py:1-269](file://services/api-gateway/main.py#L1-L269)
- [services/rag-service/main.py:1-299](file://services/rag-service/main.py#L1-L299)
- [services/retrieval-service/main.py:1-275](file://services/retrieval-service/main.py#L1-L275)
- [services/embedding-service/main.py:1-204](file://services/embedding-service/main.py#L1-L204)
- [auth/auth_manager.py:1-393](file://auth/auth_manager.py#L1-L393)
- [auth/api_routes.py:1-352](file://auth/api_routes.py#L1-L352)
- [advanced_rag/pipeline/integrated_rag.py:1-569](file://advanced_rag/pipeline/integrated_rag.py#L1-L569)

## Architecture Overview
The system employs a FastAPI microservices architecture behind an API Gateway. The gateway enforces authentication and rate limits, while downstream services collaborate to deliver RAG capabilities. Redis and MongoDB provide caching and persistence. Prometheus and Grafana enable observability.

```mermaid
graph TB
Client["Client Apps"] --> Nginx["Nginx"]
Nginx --> Gateway["API Gateway"]
Gateway --> AuthSvc["Auth Service"]
Gateway --> RAGSvc["RAG Service"]
RAGSvc --> RetSvc["Retrieval Service"]
RAGSvc --> EmbSvc["Embedding Service"]
RAGSvc --> RerSvc["Reranking Service"]
RAGSvc --> TransSvc["Translation Service"]
RAGSvc --> Redis["Redis"]
RAGSvc --> Mongo["MongoDB"]
RetSvc --> Redis
RetSvc --> Mongo
EmbSvc --> Redis
AuthSvc --> Mongo
Gateway --> Prometheus["Prometheus"]
Prometheus --> Grafana["Grafana"]
```

**Diagram sources**
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)
- [services/api-gateway/main.py:1-269](file://services/api-gateway/main.py#L1-L269)
- [services/rag-service/main.py:1-299](file://services/rag-service/main.py#L1-L299)

## Detailed Component Analysis

### API Gateway
The API Gateway centralizes ingress traffic, enforcing CORS, rate limiting, and JWT verification by delegating to the Auth Service. It exposes proxy endpoints for question answering, summarization, and quiz generation, and provides health and metrics endpoints.

```mermaid
sequenceDiagram
participant C as "Client"
participant GW as "API Gateway"
participant AUTH as "Auth Service"
participant RAG as "RAG Service"
C->>GW : POST /api/question (Authorization : Bearer <token>)
GW->>GW : check_rate_limit()
GW->>AUTH : POST /verify {token}
AUTH-->>GW : {valid}
GW->>RAG : POST /question {payload}
RAG-->>GW : {answer, sources, citations}
GW-->>C : 200 OK {result}
```

**Diagram sources**
- [services/api-gateway/main.py:126-151](file://services/api-gateway/main.py#L126-L151)
- [services/api-gateway/main.py:192-206](file://services/api-gateway/main.py#L192-L206)

Key behaviors:
- Rate limiting per IP with fail-open on Redis errors.
- JWT verification via Auth Service.
- Proxy endpoints for question, summary, and quiz.
- Health checks for Redis and downstream services.
- Prometheus metrics exposure.

**Section sources**
- [services/api-gateway/main.py:1-269](file://services/api-gateway/main.py#L1-L269)

### RAG Service
The RAG Service orchestrates the end-to-end pipeline: query preprocessing, language detection and translation, hybrid retrieval, reranking, LLM generation, and result caching. It coordinates with Retrieval, Reranking, and Translation services and integrates with Google Gemini.

```mermaid
flowchart TD
Start(["Request Received"]) --> Lang["Detect Language"]
Lang --> TranslateQ{"Needs Translation?"}
TranslateQ --> |Yes| TransQ["Translate to English"]
TranslateQ --> |No| UseQ["Use Original Query"]
TransQ --> Retrieve["Hybrid Retrieval"]
UseQ --> Retrieve
Retrieve --> Rerank["Rerank Documents"]
Rerank --> Prompt["Build Prompt with Context"]
Prompt --> LLM["LLM Generation (Gemini)"]
LLM --> TranslateA{"Back to Vietnamese?"}
TranslateA --> |Yes| TransA["Translate Answer"]
TranslateA --> |No| UseA["Use Generated Answer"]
TransA --> Cache["Cache Result"]
UseA --> Cache
Cache --> End(["Return Response"])
```

**Diagram sources**
- [services/rag-service/main.py:93-199](file://services/rag-service/main.py#L93-L199)

Operational highlights:
- Caching with Redis keys for queries and retrieval results.
- Async HTTP client for inter-service communication.
- Celery worker for asynchronous quiz generation tasks.
- Google Gemini integration for answer generation.

**Section sources**
- [services/rag-service/main.py:1-299](file://services/rag-service/main.py#L1-L299)

### Retrieval Service
Implements vector search using ChromaDB, BM25 keyword search, and hybrid fusion via Reciprocal Rank Fusion (RRF). Results are cached in Redis for performance.

```mermaid
flowchart TD
Q["Query"] --> Method{"Method"}
Method --> |vector| VS["Vector Search (ChromaDB)"]
Method --> |bm25| BM25["BM25 Keyword Search"]
Method --> |hybrid| HYB["Hybrid (RRF Fusion)"]
VS --> CacheOut["Cache Results"]
BM25 --> CacheOut
HYB --> CacheOut
CacheOut --> Return["Return Documents"]
```

**Diagram sources**
- [services/retrieval-service/main.py:155-191](file://services/retrieval-service/main.py#L155-L191)

**Section sources**
- [services/retrieval-service/main.py:1-275](file://services/retrieval-service/main.py#L1-L275)

### Embedding Service
Encodes texts into embeddings with caching, batching, and optional GPU acceleration. Supports single and batch embedding endpoints.

```mermaid
flowchart TD
In["Text(s)"] --> CacheCheck["Check Cache"]
CacheCheck --> Hit{"Cached?"}
Hit --> |Yes| Return["Return Cached Embedding(s)"]
Hit --> |No| Encode["Encode with Sentence Transformers"]
Encode --> Batch["Batch Processing"]
Batch --> Store["Store in Cache (TTL)"]
Store --> Return
```

**Diagram sources**
- [services/embedding-service/main.py:109-154](file://services/embedding-service/main.py#L109-L154)

**Section sources**
- [services/embedding-service/main.py:1-204](file://services/embedding-service/main.py#L1-L204)

### Authentication System
The Auth module manages user registration, login, JWT lifecycle, and chat history. It supports MongoDB with a JSON fallback and provides protected routes for user data and conversation management.

```mermaid
classDiagram
class AuthManager {
+hash_password(password) str
+verify_password(password, hashed) bool
+create_access_token(user_id, email, role) str
+verify_token(token) Dict
+register_user(email, username, password, full_name) Dict
+login_user(email, password) Dict
+get_user_by_id(user_id) Dict
+update_user_profile(user_id, updates) bool
+log_interaction(user_id, question, retrieved_chunks, action_type) bool
+get_weak_topics(user_id, days) list
+get_completed_topics(user_id) list
+change_password(user_id, old_password, new_password) Dict
}
class APIRoutes {
+register(RegisterRequest)
+login(LoginRequest)
+get_current_user_info(current_user)
+change_password(ChangePasswordRequest, current_user)
+create_conversation(CreateConversationRequest, current_user)
+get_conversations(limit, skip, current_user)
+get_conversation(conversation_id, current_user)
+get_conversation_messages(conversation_id, limit, current_user)
+add_message(AddMessageRequest, current_user)
+update_conversation_title(UpdateConversationTitleRequest, current_user)
+delete_conversation(conversation_id, current_user)
+search_conversations(q, limit, current_user)
+get_user_stats(current_user)
}
APIRoutes --> AuthManager : "uses"
```

**Diagram sources**
- [auth/auth_manager.py:58-393](file://auth/auth_manager.py#L58-L393)
- [auth/api_routes.py:1-352](file://auth/api_routes.py#L1-L352)

**Section sources**
- [auth/auth_manager.py:1-393](file://auth/auth_manager.py#L1-L393)
- [auth/api_routes.py:1-352](file://auth/api_routes.py#L1-L352)

### Advanced RAG Pipeline
A production-ready pipeline integrating ingestion, retrieval, reranking, generation, memory, and evaluation. It demonstrates advanced techniques such as query rewriting, contextual compression, hallucination detection, and citation grounding.

```mermaid
flowchart TD
Q["Input Query"] --> Pre["Preprocess Query"]
Pre --> Ret["Retrieve Documents"]
Ret --> ReRank["Rerank Documents"]
ReRank --> Ctx["Prepare Context"]
Ctx --> Gen["Generate Answer"]
Gen --> Post["Post-process (Citation Grounding)"]
Post --> Val["Validate Answer"]
Val --> Mem["Update Memory"]
Mem --> Eval["Evaluate Response"]
Eval --> Out["Final Response"]
```

**Diagram sources**
- [advanced_rag/pipeline/integrated_rag.py:133-240](file://advanced_rag/pipeline/integrated_rag.py#L133-L240)

**Section sources**
- [advanced_rag/pipeline/integrated_rag.py:1-569](file://advanced_rag/pipeline/integrated_rag.py#L1-L569)

## Dependency Analysis
External dependencies include LangChain, ChromaDB, Redis, MongoDB, and Google Gemini. The enterprise configuration module centralizes environment-specific settings and validation.

```mermaid
graph TB
Req["requirements.txt"] --> LC["langchain*"]
Req --> LCGG["langchain-google-genai"]
Req --> CDB["chromadb"]
Req --> ST["sentence-transformers"]
Req --> TORCH["torch"]
Req --> REDIS["redis"]
Req --> MONGO["pymongo"]
Req --> JWT["PyJWT/cryptography"]
CFG["enterprise/src/core/config.py"] --> Settings["Settings"]
Settings --> Env["Environment-based Config"]
Settings --> Secrets["Secrets Management"]
Settings --> Limits["Rate Limits & Performance"]
```

**Diagram sources**
- [requirements.txt:1-43](file://requirements.txt#L1-L43)
- [enterprise/src/core/config.py:1-200](file://enterprise/src/core/config.py#L1-L200)

**Section sources**
- [requirements.txt:1-43](file://requirements.txt#L1-L43)
- [enterprise/src/core/config.py:1-200](file://enterprise/src/core/config.py#L1-L200)

## Performance Considerations
- Caching: Redis caches embeddings, retrieval results, and RAG responses to reduce latency and cost.
- Batching: Embedding Service batches encodings to improve throughput.
- Asynchronous Processing: Celery workers handle long-running tasks like quiz generation.
- GPU Acceleration: Optional GPU usage in Embedding Service for faster encoding.
- Hybrid Retrieval: Combines vector and keyword search with RRF fusion for robustness.
- Observability: Prometheus metrics and Grafana dashboards for monitoring.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and diagnostics:
- Gateway Health: Use the health endpoint to verify Redis and downstream service availability.
- Rate Limiting: Excessive requests trigger 429 responses; inspect gateway logs and Redis counters.
- Auth Failures: Missing or invalid Authorization header leads to 401; verify token validity with the Auth Service.
- Service Connectivity: Inter-service timeouts indicate downstream service unavailability; check service health endpoints.
- Redis/Mongo Issues: Fail-open behavior may bypass rate limiting or caching; monitor service health and logs.

**Section sources**
- [services/api-gateway/main.py:156-181](file://services/api-gateway/main.py#L156-L181)
- [services/api-gateway/main.py:95-121](file://services/api-gateway/main.py#L95-L121)
- [services/api-gateway/main.py:126-151](file://services/api-gateway/main.py#L126-L151)

## Conclusion
The MinerAI backend leverages a FastAPI microservices architecture with an API Gateway for centralized control, robust caching, and coordinated orchestration among specialized services. The system integrates Google Gemini and ChromaDB, supports Redis and MongoDB for persistence and caching, and provides comprehensive observability. The design emphasizes scalability, resilience, and maintainability through modular components, asynchronous processing, and enterprise-grade configuration management.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Deployment Topology
Production deployment uses Docker Compose with Nginx as the load balancer, exposing services on dedicated ports and mounting persistent volumes for ChromaDB and Redis data.

```mermaid
graph TB
LB["Nginx (Load Balancer)"] --> GW["API Gateway"]
LB --> FE["Frontend"]
GW --> RSvc["RAG Service"]
GW --> ASvc["Auth Service"]
RSvc --> REmb["Embedding Service"]
RSvc --> RRet["Retrieval Service"]
RSvc --> RRnk["Reranking Service"]
RSvc --> TRns["Translation Service"]
GW --- Redis["Redis"]
RSvc --- Redis
GW --- Mongo["MongoDB"]
RSvc --- Mongo
LB --- Prom["Prometheus"]
Prom --- Graf["Grafana"]
```

**Diagram sources**
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)

**Section sources**
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)