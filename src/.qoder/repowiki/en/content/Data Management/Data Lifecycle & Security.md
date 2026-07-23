# Data Lifecycle & Security

<cite>
**Referenced Files in This Document**
- [metadata_enricher.py](file://metadata_enricher.py)
- [export_utils.py](file://export_utils.py)
- [rebuild_vectorstore.py](file://rebuild_vectorstore.py)
- [security/security_logger.py](file://security/security_logger.py)
- [security/encryption.py](file://security/encryption.py)
- [security/middleware.py](file://security/middleware.py)
- [security/rate_limiter.py](file://security/rate_limiter.py)
- [embed_store.py](file://embed_store.py)
- [loader.py](file://loader.py)
- [config.py](file://config.py)
- [auth/auth_manager.py](file://auth/auth_manager.py)
- [docker-compose.production.yml](file://docker-compose.production.yml)
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
This document describes data lifecycle management and security practices in MinerAI. It covers metadata enrichment processes, data export utilities, and vector store rebuilding procedures. It also explains data retention policies, backup and recovery mechanisms, and security considerations for sensitive educational data. Procedures for data anonymization, access controls, audit logging, compliance requirements, data migration, system maintenance, and disaster recovery planning are documented to ensure robust and secure operation of the system.

## Project Structure
MinerAI organizes data lifecycle and security concerns across several modules:
- Data ingestion and chunking: loader and embed_store
- Metadata enrichment: metadata_enricher
- Vector store persistence and rebuild: embed_store and rebuild_vectorstore
- Security: encryption, security_logger, middleware, rate_limiter
- Access control and auditing: auth_manager
- Configuration and deployment: config, enterprise config, docker-compose

```mermaid
graph TB
subgraph "Data Ingestion"
L["loader.py"]
ES["embed_store.py"]
end
subgraph "Metadata & Enrichment"
ME["metadata_enricher.py"]
end
subgraph "Vector Store"
VS["ChromaDB Persist"]
RV["rebuild_vectorstore.py"]
end
subgraph "Security"
ENC["security/encryption.py"]
SECLOG["security/security_logger.py"]
MID["security/middleware.py"]
RL["security/rate_limiter.py"]
end
subgraph "Access Control"
AM["auth/auth_manager.py"]
end
subgraph "Config & Ops"
CFG["config.py"]
ECFG["enterprise/src/core/config.py"]
DC["docker-compose.production.yml"]
end
L --> ES
ES --> VS
ME --> ES
RV --> VS
ENC --> ES
SECLOG --> AM
MID --> AM
RL --> AM
AM --> VS
CFG --> ES
ECFG --> DC
DC --> VS
```

**Diagram sources**
- [loader.py:1-445](file://loader.py#L1-L445)
- [embed_store.py:1-110](file://embed_store.py#L1-L110)
- [metadata_enricher.py:1-268](file://metadata_enricher.py#L1-L268)
- [rebuild_vectorstore.py:1-55](file://rebuild_vectorstore.py#L1-L55)
- [security/encryption.py:1-368](file://security/encryption.py#L1-L368)
- [security/security_logger.py:1-395](file://security/security_logger.py#L1-L395)
- [security/middleware.py:1-320](file://security/middleware.py#L1-L320)
- [security/rate_limiter.py:1-256](file://security/rate_limiter.py#L1-L256)
- [auth/auth_manager.py:1-393](file://auth/auth_manager.py#L1-L393)
- [config.py:1-218](file://config.py#L1-L218)
- [enterprise/src/core/config.py:1-200](file://enterprise/src/core/config.py#L1-L200)
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)

**Section sources**
- [loader.py:1-445](file://loader.py#L1-L445)
- [embed_store.py:1-110](file://embed_store.py#L1-L110)
- [metadata_enricher.py:1-268](file://metadata_enricher.py#L1-L268)
- [rebuild_vectorstore.py:1-55](file://rebuild_vectorstore.py#L1-L55)
- [security/encryption.py:1-368](file://security/encryption.py#L1-L368)
- [security/security_logger.py:1-395](file://security/security_logger.py#L1-L395)
- [security/middleware.py:1-320](file://security/middleware.py#L1-L320)
- [security/rate_limiter.py:1-256](file://security/rate_limiter.py#L1-L256)
- [auth/auth_manager.py:1-393](file://auth/auth_manager.py#L1-L393)
- [config.py:1-218](file://config.py#L1-L218)
- [enterprise/src/core/config.py:1-200](file://enterprise/src/core/config.py#L1-L200)
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)

## Core Components
- Metadata Enricher: Adds educational metadata to chunks (difficulty, Bloom’s level, teaching strategy, importance, keywords, prerequisites).
- Export Utilities: Provides exports to Markdown and TXT formats for conversations.
- Vector Store Rebuilder: Backs up and recreates ChromaDB vector store from source documents.
- Encryption Manager: Symmetric encryption and hashing for sensitive data.
- Security Logger: Structured security event logging with suspicious activity detection.
- Security Middleware: Input validation, sanitization, CSRF protection, and security headers.
- Rate Limiter: Sliding window rate limiting with configurable thresholds.
- Auth Manager: JWT-based authentication, password hashing, user profiles, and interaction logging.
- Configuration: Centralized settings for models, chunking, caching, logging, and rate limiting.
- Enterprise Configuration: Pydantic-based settings for production-grade deployments.
- Docker Compose: Multi-service orchestration including Redis, MongoDB, and API gateway.

**Section sources**
- [metadata_enricher.py:10-268](file://metadata_enricher.py#L10-L268)
- [export_utils.py:1-66](file://export_utils.py#L1-L66)
- [rebuild_vectorstore.py:1-55](file://rebuild_vectorstore.py#L1-L55)
- [security/encryption.py:26-368](file://security/encryption.py#L26-L368)
- [security/security_logger.py:39-395](file://security/security_logger.py#L39-L395)
- [security/middleware.py:20-320](file://security/middleware.py#L20-L320)
- [security/rate_limiter.py:21-256](file://security/rate_limiter.py#L21-L256)
- [auth/auth_manager.py:58-393](file://auth/auth_manager.py#L58-L393)
- [config.py:1-218](file://config.py#L1-L218)
- [enterprise/src/core/config.py:18-200](file://enterprise/src/core/config.py#L18-L200)
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)

## Architecture Overview
The system ingests documents, creates embeddings, persists them in ChromaDB, enriches metadata for educational context, and secures operations with encryption, rate limiting, and audit logging. Authentication integrates with MongoDB for user management and interaction logging.

```mermaid
sequenceDiagram
participant Admin as "Admin/User"
participant Loader as "loader.py"
participant Embed as "embed_store.py"
participant Enrich as "metadata_enricher.py"
participant VS as "ChromaDB"
participant Rebuild as "rebuild_vectorstore.py"
Admin->>Loader : "Select source documents"
Loader-->>Loader : "Parse and normalize metadata"
Loader->>Embed : "Pass chunks to create embeddings"
Embed->>VS : "Persist vectors and documents.pkl"
Enrich->>Embed : "Enrich chunks with metadata"
Embed-->>VS : "Updated persisted store"
Admin->>Rebuild : "Rebuild target directory"
Rebuild->>Loader : "Reload documents"
Rebuild->>Embed : "Create new vector store"
Embed-->>VS : "Persist new store"
```

**Diagram sources**
- [loader.py:396-445](file://loader.py#L396-L445)
- [embed_store.py:39-110](file://embed_store.py#L39-L110)
- [metadata_enricher.py:187-220](file://metadata_enricher.py#L187-L220)
- [rebuild_vectorstore.py:33-55](file://rebuild_vectorstore.py#L33-L55)

## Detailed Component Analysis

### Metadata Enrichment
Purpose: Enhance chunks with educational metadata to improve pedagogical relevance and retrieval quality.

Key capabilities:
- Loads course knowledge graph and derives chapter/topic metadata.
- Computes difficulty, Bloom’s taxonomy level, importance, teaching strategy, prerequisites, and keywords.
- Enriches batches of chunks and supports demo enrichment.

```mermaid
flowchart TD
Start(["Start enrichment"]) --> LoadGraph["Load course knowledge graph"]
LoadGraph --> ForEachChunk["Iterate chunks"]
ForEachChunk --> GetInfo["Resolve chapter info"]
GetInfo --> AssessDifficulty["Assess difficulty"]
AssessDifficulty --> CalcImportance["Compute importance score"]
CalcImportance --> BloomEstimate["Estimate Bloom level"]
BloomEstimate --> Strategy["Select teaching strategy"]
Strategy --> Prereq["Collect prerequisites"]
Prereq --> Keywords["Extract keywords"]
Keywords --> MergeMeta["Merge metadata into chunk"]
MergeMeta --> End(["Return enriched chunks"])
```

**Diagram sources**
- [metadata_enricher.py:32-89](file://metadata_enricher.py#L32-L89)
- [metadata_enricher.py:187-220](file://metadata_enricher.py#L187-L220)

**Section sources**
- [metadata_enricher.py:10-268](file://metadata_enricher.py#L10-L268)

### Data Export Utilities
Purpose: Provide standardized exports of conversation history for user review and archiving.

Capabilities:
- Export to Markdown with role-based sections.
- Export to plain TXT with timestamps and roles.
- Formatting helper for UI display.

```mermaid
flowchart TD
Start(["Export request"]) --> ChooseFormat{"Choose format"}
ChooseFormat --> |Markdown| MD["Render Markdown"]
ChooseFormat --> |TXT| TXT["Render TXT"]
MD --> SaveMD["Write to exports/<timestamp>.md"]
TXT --> SaveTXT["Write to exports/<timestamp>.txt"]
SaveMD --> Done(["Return file path"])
SaveTXT --> Done
```

**Diagram sources**
- [export_utils.py:11-31](file://export_utils.py#L11-L31)
- [export_utils.py:34-55](file://export_utils.py#L34-L55)

**Section sources**
- [export_utils.py:1-66](file://export_utils.py#L1-L66)

### Vector Store Rebuilding
Purpose: Safely back up and rebuild the ChromaDB vector store during maintenance or upgrades.

Process:
- Backup existing directory to a “_backup” sibling.
- Delete old directory; handle permission locks by renaming.
- Reload documents from data/, create embeddings, persist to target directory.

```mermaid
flowchart TD
Start(["Start rebuild"]) --> Confirm{"Confirm or --force"}
Confirm --> Backup["Copy target to *_backup"]
Backup --> DeleteOld["Delete target directory"]
DeleteOld --> Reload["Load documents from data/"]
Reload --> CreateStore["Create vector store with embeddings"]
CreateStore --> Persist["Persist to target directory"]
Persist --> Done(["Rebuild complete"])
```

**Diagram sources**
- [rebuild_vectorstore.py:12-55](file://rebuild_vectorstore.py#L12-L55)
- [embed_store.py:39-66](file://embed_store.py#L39-L66)
- [loader.py:396-445](file://loader.py#L396-L445)

**Section sources**
- [rebuild_vectorstore.py:1-55](file://rebuild_vectorstore.py#L1-L55)
- [embed_store.py:1-110](file://embed_store.py#L1-L110)
- [loader.py:1-445](file://loader.py#L1-L445)

### Security Logging and Audit Trail
Purpose: Maintain a structured, auditable record of security events with suspicious activity detection.

Key features:
- Enumerated event types (login, logout, registration, data access/modification, rate limit exceeded, encryption/authentication errors).
- JSON-formatted logs with timestamps, user identity, IP, and severity.
- Suspicious activity detection and alerting thresholds.
- Statistics aggregation and recent event retrieval.

```mermaid
classDiagram
class SecurityLogger {
+log_event(...)
+log_login_success(...)
+log_login_failed(...)
+log_logout(...)
+log_registration(...)
+log_password_change(...)
+log_unauthorized_access(...)
+log_rate_limit_exceeded(...)
+log_data_access(...)
+log_data_modification(...)
+log_api_key_used(...)
+log_encryption_error(...)
+log_authentication_error(...)
+get_recent_events(...)
+get_stats() Dict
}
class SecurityEventType {
<<enumeration>>
+LOGIN_SUCCESS
+LOGIN_FAILED
+LOGOUT
+REGISTRATION
+PASSWORD_CHANGE
+UNAUTHORIZED_ACCESS
+RATE_LIMIT_EXCEEDED
+SUSPICIOUS_ACTIVITY
+DATA_ACCESS
+DATA_MODIFICATION
+API_KEY_USED
+ENCRYPTION_ERROR
+AUTHENTICATION_ERROR
}
SecurityLogger --> SecurityEventType : "uses"
```

**Diagram sources**
- [security/security_logger.py:22-395](file://security/security_logger.py#L22-L395)

**Section sources**
- [security/security_logger.py:1-395](file://security/security_logger.py#L1-L395)

### Encryption and Data Protection
Purpose: Protect sensitive data at rest and in transit using symmetric encryption and hashing.

Highlights:
- Fernet-based symmetric encryption with environment-managed keys.
- PBKDF2-derived keys from passwords.
- Encryption/decryption of conversation histories, individual fields, and dictionaries.
- Hashing and verification utilities.

```mermaid
classDiagram
class EncryptionManager {
+encrypt(data) str
+decrypt(encrypted, return_type) Union
+encrypt_conversation(list) str
+decrypt_conversation(encrypted) list
+encrypt_field(value) str
+decrypt_field(encrypted) str
+encrypt_dict(dict, fields) dict
+decrypt_dict(dict, fields) dict
+hash_data(data) str
+verify_hash(data, hash) bool
}
class SecureStorage {
+save_encrypted(data, path) void
+load_encrypted(path) dict
+encrypt_mongodb_document(doc, fields) dict
+decrypt_mongodb_document(doc, fields) dict
}
SecureStorage --> EncryptionManager : "uses"
```

**Diagram sources**
- [security/encryption.py:26-307](file://security/encryption.py#L26-L307)

**Section sources**
- [security/encryption.py:1-368](file://security/encryption.py#L1-L368)

### Security Middleware and Input Sanitization
Purpose: Prevent common attacks and sanitize inputs across the platform.

Capabilities:
- SQL injection and XSS pattern detection.
- HTML escaping and null-byte removal.
- CSRF token generation and verification.
- Security headers for CSP, HSTS, frame options, etc.
- Email and username validation.
- Filename sanitization and allowed extension checks.

```mermaid
flowchart TD
Start(["Incoming input"]) --> Validate["Validate length and patterns"]
Validate --> |Invalid| Error["Raise validation error"]
Validate --> |Valid| Sanitize["HTML escape and remove null bytes"]
Sanitize --> Headers["Add security headers"]
Headers --> Proceed(["Proceed to processing"])
```

**Diagram sources**
- [security/middleware.py:49-124](file://security/middleware.py#L49-L124)

**Section sources**
- [security/middleware.py:1-320](file://security/middleware.py#L1-L320)

### Rate Limiting
Purpose: Protect APIs from abuse with sliding window rate limiting.

Behavior:
- Tracks requests per minute, hour, and day.
- Blocks clients exceeding thresholds with escalating durations.
- Provides remaining requests and statistics.

```mermaid
flowchart TD
Start(["Request received"]) --> CheckBlocked{"Client blocked?"}
CheckBlocked --> |Yes| Block["Return block reason"]
CheckBlocked --> |No| CountMinute["Count requests in last minute"]
CountMinute --> MinuteAllowed{"Within minute limit?"}
MinuteAllowed --> |No| BlockMinute["Block for 1 minute"]
MinuteAllowed --> |Yes| CountHour["Count requests in last hour"]
CountHour --> HourAllowed{"Within hour limit?"}
HourAllowed --> |No| BlockHour["Block for 5 minutes"]
HourAllowed --> |Yes| CountDay["Count requests in last day"]
CountDay --> DayAllowed{"Within day limit?"}
DayAllowed --> |No| BlockDay["Block for 1 hour"]
DayAllowed --> |Yes| Record["Record request"] --> Allow(["Allow request"])
```

**Diagram sources**
- [security/rate_limiter.py:81-126](file://security/rate_limiter.py#L81-L126)

**Section sources**
- [security/rate_limiter.py:1-256](file://security/rate_limiter.py#L1-L256)

### Access Controls and Authentication
Purpose: Manage user identities, enforce authorization, and maintain interaction logs.

Features:
- JWT-based access tokens with expiration.
- Password hashing using bcrypt.
- Fallback to local JSON storage when MongoDB is unavailable.
- Interaction logging for pedagogical analytics.
- Weak topic and completed topic discovery from logs.

```mermaid
sequenceDiagram
participant Client as "Client"
participant Auth as "AuthManager"
participant Mongo as "MongoDB"
participant Token as "JWT"
Client->>Auth : "Register(email, username, password)"
Auth->>Auth : "Hash password"
Auth->>Mongo : "Insert user document"
Mongo-->>Auth : "Success"
Auth-->>Client : "Registration result"
Client->>Auth : "Login(email, password)"
Auth->>Mongo : "Find user"
Mongo-->>Auth : "User document"
Auth->>Auth : "Verify password"
Auth->>Token : "Create access token"
Auth-->>Client : "Token and user info"
```

**Diagram sources**
- [auth/auth_manager.py:126-217](file://auth/auth_manager.py#L126-L217)

**Section sources**
- [auth/auth_manager.py:1-393](file://auth/auth_manager.py#L1-L393)

### Configuration and Deployment
Purpose: Centralize configuration and define production-grade deployment topology.

Highlights:
- Centralized settings for models, chunking, caching, logging, and rate limiting.
- Enterprise configuration with Pydantic validation and environment-specific overrides.
- Docker Compose orchestrates API gateway, frontend, services, Redis, MongoDB, and monitoring.

```mermaid
graph TB
DC["docker-compose.production.yml"] --> NGINX["nginx"]
DC --> APIGW["api-gateway"]
DC --> FE["frontend"]
DC --> RAG["rag-service"]
DC --> EMB["embedding-service"]
DC --> RET["retrieval-service"]
DC --> RER["reranking-service"]
DC --> TR["translation-service"]
DC --> AUTH["auth-service"]
DC --> CEL["celery-worker / celery-beat"]
DC --> REDIS["redis"]
DC --> MONGO["mongodb"]
DC --> MON["monitoring (Prometheus/Grafana)"]
```

**Diagram sources**
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)
- [config.py:1-218](file://config.py#L1-L218)
- [enterprise/src/core/config.py:1-200](file://enterprise/src/core/config.py#L1-L200)

**Section sources**
- [config.py:1-218](file://config.py#L1-L218)
- [enterprise/src/core/config.py:1-200](file://enterprise/src/core/config.py#L1-L200)
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)

## Dependency Analysis
- Loader depends on LangChain document loaders and configuration for embedding model selection.
- Embed store depends on loader outputs and persists to ChromaDB with documents.pkl for BM25 indexing.
- Metadata enricher depends on course knowledge graph and enriches chunk metadata prior to persistence.
- Security components are standalone but integrate with auth and API layers.
- Enterprise configuration complements development config for production deployments.

```mermaid
graph LR
Loader["loader.py"] --> Embed["embed_store.py"]
Embed --> VS["ChromaDB"]
Enrich["metadata_enricher.py"] --> Embed
Auth["auth/auth_manager.py"] --> VS
SecLog["security/security_logger.py"] --> Auth
Enc["security/encryption.py"] --> Embed
Mid["security/middleware.py"] --> Auth
RL["security/rate_limiter.py"] --> Auth
CFG["config.py"] --> Embed
ECFG["enterprise/src/core/config.py"] --> DC["docker-compose.production.yml"]
```

**Diagram sources**
- [loader.py:1-445](file://loader.py#L1-L445)
- [embed_store.py:1-110](file://embed_store.py#L1-L110)
- [metadata_enricher.py:1-268](file://metadata_enricher.py#L1-L268)
- [auth/auth_manager.py:1-393](file://auth/auth_manager.py#L1-L393)
- [security/security_logger.py:1-395](file://security/security_logger.py#L1-L395)
- [security/encryption.py:1-368](file://security/encryption.py#L1-L368)
- [security/middleware.py:1-320](file://security/middleware.py#L1-L320)
- [security/rate_limiter.py:1-256](file://security/rate_limiter.py#L1-L256)
- [config.py:1-218](file://config.py#L1-L218)
- [enterprise/src/core/config.py:1-200](file://enterprise/src/core/config.py#L1-L200)
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)

**Section sources**
- [loader.py:1-445](file://loader.py#L1-L445)
- [embed_store.py:1-110](file://embed_store.py#L1-L110)
- [metadata_enricher.py:1-268](file://metadata_enricher.py#L1-L268)
- [auth/auth_manager.py:1-393](file://auth/auth_manager.py#L1-L393)
- [security/security_logger.py:1-395](file://security/security_logger.py#L1-L395)
- [security/encryption.py:1-368](file://security/encryption.py#L1-L368)
- [security/middleware.py:1-320](file://security/middleware.py#L1-L320)
- [security/rate_limiter.py:1-256](file://security/rate_limiter.py#L1-L256)
- [config.py:1-218](file://config.py#L1-L218)
- [enterprise/src/core/config.py:1-200](file://enterprise/src/core/config.py#L1-L200)
- [docker-compose.production.yml:1-359](file://docker-compose.production.yml#L1-L359)

## Performance Considerations
- Embedding caching and batch sizes reduce latency and resource usage.
- Hybrid retrieval and optional reranking balance recall and precision.
- Rate limiting prevents overload and ensures fair usage.
- Vector store persistence and BM25 documents.pkl enable fast reloads.
- Containerized deployment with resource limits and health checks improves stability.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Vector store rebuild fails due to locked files: rename target directory and retry after stopping backend.
- Permission denied on deletion: ensure backend is stopped; the rebuild script handles renaming to avoid data loss.
- Security logger not capturing events: verify log directory creation and file permissions.
- Encryption key missing: set ENCRYPTION_KEY in environment; the manager can generate a new key for development.
- Rate limit exceeded: adjust thresholds or wait for cooldown windows.
- Authentication failures: confirm JWT secret, MongoDB connectivity, and user credentials.

**Section sources**
- [rebuild_vectorstore.py:19-31](file://rebuild_vectorstore.py#L19-L31)
- [security/security_logger.py:50-52](file://security/security_logger.py#L50-L52)
- [security/encryption.py:38-53](file://security/encryption.py#L38-L53)
- [security/rate_limiter.py:81-126](file://security/rate_limiter.py#L81-L126)
- [auth/auth_manager.py:61-87](file://auth/auth_manager.py#L61-L87)

## Conclusion
MinerAI implements a comprehensive data lifecycle and security framework. Documents are ingested, enriched with pedagogical metadata, embedded, and persisted in ChromaDB. Security is enforced through encryption, rate limiting, input sanitization, audit logging, and robust authentication. Configuration and deployment artifacts support scalable, production-ready operations with clear procedures for maintenance, migration, and disaster recovery.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Data Retention Policies
- Logs: Managed by centralized logging configuration with rotation and retention limits.
- Conversations: Exportable via export utilities; consider retention periods aligned with institutional policy.
- Vector store: Rebuilds preserve BM25 documents.pkl; backups are maintained during rebuilds.

**Section sources**
- [config.py:122-127](file://config.py#L122-L127)
- [export_utils.py:11-31](file://export_utils.py#L11-L31)
- [rebuild_vectorstore.py:12-18](file://rebuild_vectorstore.py#L12-L18)

### Backup and Recovery Mechanisms
- Vector store backup: Automatic backup to a sibling “_backup” directory during rebuild.
- Persistence: ChromaDB persists vectors; documents.pkl stored alongside for BM25.
- Disaster recovery: Restore from backup directory; redeploy services via Docker Compose.

**Section sources**
- [rebuild_vectorstore.py:12-18](file://rebuild_vectorstore.py#L12-L18)
- [embed_store.py:61-64](file://embed_store.py#L61-L64)

### Security Considerations for Sensitive Educational Data
- Encryption: Use EncryptionManager for sensitive fields and conversation histories.
- Logging: SecurityLogger records security events with structured JSON for auditability.
- Input validation: SecurityMiddleware protects against SQL injection and XSS.
- Access control: AuthManager enforces JWT-based authentication and password hashing.
- Rate limiting: RateLimiter mitigates abuse and protects system resources.

**Section sources**
- [security/encryption.py:26-176](file://security/encryption.py#L26-L176)
- [security/security_logger.py:94-137](file://security/security_logger.py#L94-L137)
- [security/middleware.py:49-98](file://security/middleware.py#L49-L98)
- [auth/auth_manager.py:88-125](file://auth/auth_manager.py#L88-L125)
- [security/rate_limiter.py:81-126](file://security/rate_limiter.py#L81-L126)

### Data Anonymization Techniques
- Export utilities produce human-readable formats suitable for sharing without personal identifiers.
- Consider removing or hashing personally identifiable information before publishing exports.

**Section sources**
- [export_utils.py:11-31](file://export_utils.py#L11-L31)

### Access Controls and Compliance Requirements
- Authentication: JWT tokens with configurable expiration; bcrypt password hashing.
- Authorization: Role-based access via user roles; MongoDB indexes for uniqueness.
- Auditing: SecurityLogger maintains audit trails; AuthManager logs interactions for analytics.
- Compliance: Centralized configuration supports environment-specific settings; enterprise config validates inputs.

**Section sources**
- [auth/auth_manager.py:101-125](file://auth/auth_manager.py#L101-L125)
- [auth/auth_manager.py:174-217](file://auth/auth_manager.py#L174-L217)
- [security/security_logger.py:296-357](file://security/security_logger.py#L296-L357)
- [config.py:138-160](file://config.py#L138-L160)
- [enterprise/src/core/config.py:136-148](file://enterprise/src/core/config.py#L136-L148)

### Procedures for Data Migration, Maintenance, and Disaster Recovery
- Migration: Rebuild vector store to new target directory; ensure backup exists; restart services.
- Maintenance: Use rebuild script with confirmation or force flag; monitor logs and statistics.
- Disaster recovery: Restore from “_backup” directory; validate vector counts and document loads.

**Section sources**
- [rebuild_vectorstore.py:46-55](file://rebuild_vectorstore.py#L46-L55)
- [embed_store.py:68-100](file://embed_store.py#L68-L100)