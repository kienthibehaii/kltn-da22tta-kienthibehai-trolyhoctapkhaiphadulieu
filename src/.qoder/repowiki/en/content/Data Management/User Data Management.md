# User Data Management

<cite>
**Referenced Files in This Document**
- [auth_manager.py](file://auth/auth_manager.py)
- [chat_history_manager.py](file://auth/chat_history_manager.py)
- [api_routes.py](file://auth/api_routes.py)
- [user_routes.py](file://auth/user_routes.py)
- [learning_context_manager.py](file://educational_engine/learning_context_manager.py)
- [learning_progress_tracker.py](file://learning_progress_tracker.py)
- [conversation_history.py](file://conversation_history.py)
- [config.py](file://config.py)
- [main.py](file://backend/main.py)
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

## Introduction
This document describes the user data management subsystems in MinerAI, focusing on:
- MongoDB schema design for user profiles, chat history, and learning progress
- Chat history manager functionality and persistence strategies
- Learning analytics data collection and progress tracking
- Authentication and session management
- Preference storage and progress monitoring
- Data validation rules, indexing strategies, and lifecycle management

## Project Structure
MinerAI organizes user data management across several modules:
- Authentication and user profile management
- Chat history persistence and retrieval
- Learning context and progress tracking
- Configuration and backend entrypoint

```mermaid
graph TB
subgraph "Backend"
API["FastAPI App<br/>backend/main.py"]
AuthRoutes["Auth Routes<br/>auth/api_routes.py"]
UserRoutes["User Routes<br/>auth/user_routes.py"]
AuthMgr["Auth Manager<br/>auth/auth_manager.py"]
ChatMgr["Chat History Manager<br/>auth/chat_history_manager.py"]
LCtxMgr["Learning Context Manager<br/>educational_engine/learning_context_manager.py"]
LPT["Learning Progress Tracker<br/>learning_progress_tracker.py"]
ConvHist["Conversation History<br/>conversation_history.py"]
end
API --> AuthRoutes
API --> UserRoutes
AuthRoutes --> AuthMgr
AuthRoutes --> ChatMgr
UserRoutes --> AuthMgr
LCtxMgr --> AuthMgr
LPT --> AuthMgr
ConvHist --> AuthMgr
```

**Diagram sources**
- [main.py:25-41](file://backend/main.py#L25-L41)
- [api_routes.py:15-15](file://auth/api_routes.py#L15-L15)
- [user_routes.py:7-7](file://auth/user_routes.py#L7-L7)
- [auth_manager.py:58-82](file://auth/auth_manager.py#L58-L82)
- [chat_history_manager.py:21-37](file://auth/chat_history_manager.py#L21-L37)
- [learning_context_manager.py:23-40](file://educational_engine/learning_context_manager.py#L23-L40)
- [learning_progress_tracker.py:58-108](file://learning_progress_tracker.py#L58-L108)
- [conversation_history.py:10-43](file://conversation_history.py#L10-L43)

**Section sources**
- [main.py:11-69](file://backend/main.py#L11-L69)
- [config.py:46-46](file://config.py#L46-L46)

## Core Components
- Authentication and user profile management: handles registration, login, JWT token creation/verification, password hashing, and user profile updates. It also logs interactions and computes weak/completed topics for learning analytics.
- Chat history manager: persists conversations and messages, supports CRUD operations, pagination, search, and statistics.
- Learning context manager: maintains user learning profiles, tracks interactions, detects learning patterns, and recommends difficulty and next concepts.
- Learning progress tracker: records student-system interactions and quiz responses, computes mastery and progress statistics.
- Conversation history: manages session-based chat history with optional MongoDB or local JSON fallback and trimming strategies.
- API routes: expose endpoints for authentication, chat history, user stats, and personal question bank.

**Section sources**
- [auth_manager.py:58-393](file://auth/auth_manager.py#L58-L393)
- [chat_history_manager.py:21-274](file://auth/chat_history_manager.py#L21-L274)
- [learning_context_manager.py:23-40](file://educational_engine/learning_context_manager.py#L23-L40)
- [learning_progress_tracker.py:58-463](file://learning_progress_tracker.py#L58-L463)
- [conversation_history.py:10-302](file://conversation_history.py#L10-L302)
- [api_routes.py:15-352](file://auth/api_routes.py#L15-L352)

## Architecture Overview
The user data management architecture integrates authentication, chat persistence, and learning analytics into a cohesive system with MongoDB as the primary datastore and JSON fallback for offline scenarios.

```mermaid
graph TB
Client["Client"]
API["FastAPI Router<br/>auth/api_routes.py"]
UserAPI["User Router<br/>auth/user_routes.py"]
Auth["AuthManager<br/>auth/auth_manager.py"]
Chat["ChatHistoryManager<br/>auth/chat_history_manager.py"]
LCtx["LearningContextManager<br/>educational_engine/learning_context_manager.py"]
LProg["LearningProgressTracker<br/>learning_progress_tracker.py"]
Conv["ConversationHistory<br/>conversation_history.py"]
Client --> API
Client --> UserAPI
API --> Auth
API --> Chat
UserAPI --> Auth
LCtx --> Auth
LProg --> Auth
Conv --> Auth
```

**Diagram sources**
- [api_routes.py:15-15](file://auth/api_routes.py#L15-L15)
- [user_routes.py:7-7](file://auth/user_routes.py#L7-L7)
- [auth_manager.py:58-82](file://auth/auth_manager.py#L58-L82)
- [chat_history_manager.py:21-37](file://auth/chat_history_manager.py#L21-L37)
- [learning_context_manager.py:23-40](file://educational_engine/learning_context_manager.py#L23-L40)
- [learning_progress_tracker.py:58-108](file://learning_progress_tracker.py#L58-L108)
- [conversation_history.py:10-43](file://conversation_history.py#L10-L43)

## Detailed Component Analysis

### Authentication and User Profile Management
- Responsibilities:
  - Registration with validation and password hashing
  - Login with JWT token issuance and last login update
  - Token verification for protected endpoints
  - User profile retrieval and updates
  - Interaction logging for analytics
  - Weak topics and completed topics computation
  - Password change with validation
- Data persistence:
  - MongoDB users collection with unique indexes on email and username
  - Optional JSON fallback for user storage when MongoDB is unavailable
- Security:
  - Bcrypt password hashing
  - HS256 JWT with configurable secret and expiration
  - Access controlled via Authorization header bearer tokens

```mermaid
classDiagram
class AuthManager {
+hash_password(password) string
+verify_password(password, hashed) bool
+create_access_token(user_id, email, role) string
+verify_token(token) dict
+register_user(email, username, password, full_name) dict
+login_user(email, password) dict
+get_user_by_id(user_id) dict
+update_user_profile(user_id, updates) bool
+log_interaction(user_id, question, retrieved_chunks, action_type) bool
+get_weak_topics(user_id, days) list
+get_completed_topics(user_id) list
+change_password(user_id, old_password, new_password) dict
}
```

**Diagram sources**
- [auth_manager.py:58-393](file://auth/auth_manager.py#L58-L393)

**Section sources**
- [auth_manager.py:58-393](file://auth/auth_manager.py#L58-L393)
- [api_routes.py:58-138](file://auth/api_routes.py#L58-L138)

### Chat History Management
- Responsibilities:
  - Create conversations with metadata and timestamps
  - Add messages with roles and optional metadata
  - Retrieve conversation messages with pagination
  - List user conversations with last message preview
  - Update conversation title and soft-delete conversations
  - Search conversations by title
  - Compute user conversation statistics
- Persistence:
  - MongoDB conversations and messages collections
  - Indexes on user_id, created_at, conversation_id, and created_at
- Ownership and permissions:
  - All operations validate conversation ownership before acting

```mermaid
classDiagram
class ChatHistoryManager {
+create_conversation(user_id, title) string
+add_message(conversation_id, role, content, metadata) string
+get_conversation_messages(conversation_id, limit) list
+get_user_conversations(user_id, limit, skip) list
+get_conversation(conversation_id) dict
+update_conversation_title(conversation_id, title) bool
+delete_conversation(conversation_id) bool
+search_conversations(user_id, query, limit) list
+get_conversation_stats(user_id) dict
}
```

**Diagram sources**
- [chat_history_manager.py:21-274](file://auth/chat_history_manager.py#L21-L274)

**Section sources**
- [chat_history_manager.py:21-274](file://auth/chat_history_manager.py#L21-L274)
- [api_routes.py:167-352](file://auth/api_routes.py#L167-L352)

### Learning Context and Analytics
- Responsibilities:
  - Build or retrieve user learning profiles with topics, strengths, weaknesses, and engagement metrics
  - Track interactions and update profiles accordingly
  - Detect learning patterns over time windows
  - Recommend difficulty levels and next concepts
  - Calculate mastery levels and mark weak areas
  - Provide learning summaries and recommendations
- Persistence:
  - MongoDB collections for user profiles and interactions
  - Indexes on user_id and timestamp for performance

```mermaid
classDiagram
class LearningContextManager {
+build_user_profile(user_id) dict
+track_interaction(user_id, question, question_type, concepts, difficulty_used, timestamp) void
+detect_learning_pattern(user_id, window_days) dict
+recommend_difficulty_level(user_id) string
+identify_weak_areas(user_id, window_days) list
+identify_strong_areas(user_id) list
+personalize_response(response, user_profile) dict
+get_learning_summary(user_id) dict
+track_confusion_signal(user_id, question_id, confusion_signals) void
+get_remedial_content_for_concept(user_id, concept) dict
+calculate_mastery_level(user_id, concept) string
+suggest_next_concept(user_id, limit) list
}
```

**Diagram sources**
- [learning_context_manager.py:23-629](file://educational_engine/learning_context_manager.py#L23-L629)

**Section sources**
- [learning_context_manager.py:23-629](file://educational_engine/learning_context_manager.py#L23-L629)

### Learning Progress Tracking
- Responsibilities:
  - Create student profiles and record interactions and quiz responses
  - Update mastery levels per chapter and student
  - Compute progress statistics and weak/strong areas
  - Support both MongoDB and in-memory modes
- Persistence:
  - MongoDB collections for student profiles, interactions, quiz responses, and mastery levels
  - Indexes on student_id for efficient queries

```mermaid
classDiagram
class LearningProgressTracker {
+create_student_profile(student_id, name, email, major) StudentProfile
+record_interaction(student_id, chapter_id, topic, query, strategy_used, response_quality, mastery_gain) InteractionRecord
+record_quiz_response(student_id, quiz_id, chapter_id, question, student_answer, correct_answer, score, time_taken) QuizResponse
+get_student_progress(student_id) dict
+get_weak_areas(student_id, threshold) list
+get_strong_areas(student_id, threshold) list
}
class StudentProfile {
+string student_id
+string name
+string email
+string major
+datetime created_at
+string preferred_strategy
+string learning_pace
+string current_chapter
+float overall_mastery
+int total_interactions
+datetime last_active
}
class InteractionRecord {
+string student_id
+string interaction_id
+datetime timestamp
+string chapter_id
+string topic
+string query
+string strategy_used
+float response_quality
+string student_feedback
+float mastery_gain
}
class QuizResponse {
+string student_id
+string quiz_id
+string chapter_id
+string question
+string student_answer
+string correct_answer
+float score
+datetime attempted_at
+int time_taken
+bool is_correct
}
LearningProgressTracker --> StudentProfile : "manages"
LearningProgressTracker --> InteractionRecord : "records"
LearningProgressTracker --> QuizResponse : "records"
```

**Diagram sources**
- [learning_progress_tracker.py:58-463](file://learning_progress_tracker.py#L58-L463)

**Section sources**
- [learning_progress_tracker.py:58-463](file://learning_progress_tracker.py#L58-L463)

### Conversation History (Session-based)
- Responsibilities:
  - Save messages with roles and citations
  - Retrieve histories with limits and context formatting
  - Trim histories to a maximum number of turns
  - Clear session histories and summarize sessions
  - Fallback to local JSON storage when MongoDB is unavailable
- Persistence:
  - MongoDB conversations collection with automatic trimming
  - Local JSON file fallback with configurable max history

```mermaid
classDiagram
class ConversationHistory {
+save_message(session_id, role, content, citations) void
+get_history(session_id, limit) list
+get_context_for_llm(session_id, max_turns) string
+get_recent_messages(session_id, n) list
+clear_history(session_id) void
+get_all_sessions() list
+get_session_summary(session_id) dict
+close() void
}
```

**Diagram sources**
- [conversation_history.py:10-302](file://conversation_history.py#L10-L302)

**Section sources**
- [conversation_history.py:10-302](file://conversation_history.py#L10-L302)

### API Endpoints and Authentication Flow
- Authentication endpoints:
  - Register, login, get current user, change password
  - Protected routes via Authorization header bearer tokens
- Chat history endpoints:
  - Create, list, get, add message, update title, delete, search, and stats
  - Ownership checks enforced on all operations
- User analytics endpoints:
  - Weak topics and completed topics derived from interaction logs

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "Auth Router<br/>auth/api_routes.py"
participant Auth as "AuthManager<br/>auth/auth_manager.py"
participant DB as "MongoDB"
Client->>API : POST /api/auth/login
API->>Auth : login_user(email, password)
Auth->>DB : find user by email
DB-->>Auth : user document
Auth->>Auth : verify password
Auth->>DB : update last_login
Auth-->>API : token + user info
API-->>Client : {token, user}
```

**Diagram sources**
- [api_routes.py:97-109](file://auth/api_routes.py#L97-L109)
- [auth_manager.py:174-218](file://auth/auth_manager.py#L174-L218)

**Section sources**
- [api_routes.py:58-138](file://auth/api_routes.py#L58-L138)
- [api_routes.py:167-352](file://auth/api_routes.py#L167-L352)

## Dependency Analysis
- External dependencies:
  - MongoDB via PyMongo for persistent storage
  - JWT library for token handling
  - Bcrypt for secure password hashing
  - Python dotenv for environment configuration
- Internal dependencies:
  - API routers depend on AuthManager and ChatHistoryManager
  - LearningContextManager depends on AuthManager for user identity
  - LearningProgressTracker optionally depends on MongoDB
  - ConversationHistory supports both MongoDB and JSON fallback

```mermaid
graph LR
AuthMgr["AuthManager"]
ChatMgr["ChatHistoryManager"]
LCtxMgr["LearningContextManager"]
LPT["LearningProgressTracker"]
Conv["ConversationHistory"]
Mongo["MongoDB"]
JWT["JWT"]
Bcrypt["bcrypt"]
AuthMgr --> Mongo
ChatMgr --> Mongo
LCtxMgr --> Mongo
LPT --> Mongo
Conv --> Mongo
AuthMgr --> JWT
AuthMgr --> Bcrypt
```

**Diagram sources**
- [auth_manager.py:58-393](file://auth/auth_manager.py#L58-L393)
- [chat_history_manager.py:21-274](file://auth/chat_history_manager.py#L21-L274)
- [learning_context_manager.py:23-629](file://educational_engine/learning_context_manager.py#L23-L629)
- [learning_progress_tracker.py:58-108](file://learning_progress_tracker.py#L58-L108)
- [conversation_history.py:10-43](file://conversation_history.py#L10-L43)

**Section sources**
- [auth_manager.py:58-393](file://auth/auth_manager.py#L58-L393)
- [chat_history_manager.py:21-37](file://auth/chat_history_manager.py#L21-L37)
- [learning_context_manager.py:23-40](file://educational_engine/learning_context_manager.py#L23-L40)
- [learning_progress_tracker.py:58-108](file://learning_progress_tracker.py#L58-L108)
- [conversation_history.py:10-43](file://conversation_history.py#L10-L43)

## Performance Considerations
- Indexing strategies:
  - Users: unique indexes on email and username
  - Conversations: indexes on user_id and created_at
  - Messages: indexes on conversation_id and created_at
  - Learning profiles and interactions: indexes on user_id and timestamp
- Query patterns:
  - Pagination via limit/skip and sort by updated_at/created_at
  - Regex-based search for conversation titles
  - Aggregation-style counts for statistics
- Fallback behavior:
  - JSON storage when MongoDB is unavailable prevents downtime
- Resource constraints:
  - Configurable max history for session-based chat
  - Automatic trimming to keep collections lean

**Section sources**
- [auth_manager.py:78-80](file://auth/auth_manager.py#L78-L80)
- [chat_history_manager.py:32-36](file://auth/chat_history_manager.py#L32-L36)
- [learning_context_manager.py:36-40](file://educational_engine/learning_context_manager.py#L36-L40)
- [conversation_history.py:22-42](file://conversation_history.py#L22-L42)
- [config.py:117-118](file://config.py#L117-L118)

## Troubleshooting Guide
- Authentication issues:
  - Missing JWT_SECRET_KEY triggers a warning and uses an insecure default; set a strong secret in production.
  - MongoDB connectivity failures fall back to JSON storage; verify MONGODB_URI and network access.
- Chat history errors:
  - Ownership validation denies access to unauthorized operations; ensure the current user owns the target conversation.
  - Message addition increments conversation counters and auto-updates titles for first user messages.
- Learning analytics:
  - Weak topics computed from interaction logs; ensure logs are populated and recent activity exists.
  - Completed topics derived from quiz-generated actions; verify action types and logging.
- Session and history:
  - ConversationHistory trims older messages automatically; adjust max_history as needed.
  - JSON fallback preserves recent messages and caps growth.

**Section sources**
- [auth_manager.py:21-34](file://auth/auth_manager.py#L21-L34)
- [auth_manager.py:85-87](file://auth/auth_manager.py#L85-L87)
- [api_routes.py:216-223](file://auth/api_routes.py#L216-L223)
- [conversation_history.py:202-231](file://conversation_history.py#L202-L231)

## Conclusion
MinerAI’s user data management system combines robust authentication, resilient chat history persistence, and comprehensive learning analytics. It leverages MongoDB for scalable data storage with sensible indexing and gracefully falls back to JSON when needed. The modular design ensures clear separation of concerns while enabling seamless integration across authentication, chat, and learning components.