## v0.3.0 (2026-01-15)

### BREAKING CHANGE

- NotificationType enum values changed from lowercase to uppercase
- AlreadyExistsError now returns HTTP 409 Conflict instead of 400 Bad Request

### Feat

- **documents**: Add preview URL endpoint and enhance download documentation
- **database**: Add comprehensive sample data with MinIO integration
- **engagement**: Add mission engagement listing endpoint with volunteer details
- **notifications**: TA-93 Implement in-app and email notification system
- **auth**: TA-93 Add password reset, admin tools, and auth profile
- **mission**: TA-93 Implement multi-category missions & category management
- **admin**: TA-93 Add endpoints for volunteer, mission, report, and document mgmt
- **verification**: TA-93 Implement document verification for associations
- **auth**: TA-93 Add hashed refresh token storage and rotation
- **association**: TA-93 Implement full CRUD & rate limit auth endpoints

### Fix

- **init_dev_data**: Remove is_read from NotificationCreate call
- **notification**: Change NotificationType enum to uppercase values
- **database**: Use service layer for sample data creation
- Improve input validation and refactor engagement service
- **docs,validation**: Fix field names and add mission validation
- **cors**: Refactor CORS origin parsing for cleaner architecture
- Change AlreadyExistsError status code from 400 to 409
- **db**: TA-93 Makes user dates timezone-aware; fixes notification index
- **migration**: TA-93 Corrects timezone for DateTime in downgrade
- **api**: Add latest association document endpoint & engagement public model
- **db**: TA-93 Finalize transactions and extract profile service
- TA-93 Clamp volunteer count after mission leave
- TA-93 Reorder mission leave operations for atomicity

### Refactor

- Rename  key to  and update sample emails
- **init**: Remove automatic sample data initialization
- Make sample data initialization conditional and rename file
- **document**: Extract _validate_document_pending helper
- **service**: Extract get_or_404 helper to reduce DRY violations
- **service**: Standardize create_document signature to Pattern B
- **docs**: Standardize backtick formatting and enum comparisons
- **notification**: Use min_length for Field validation
- TA-93 Convert volunteer application withdrawal to sync, update DB schema
- **volunteer**: Move association email send out of notification try and ran alembic rev
- **services**: Consolidate imports at module level
- TA-93 Standardize enum values and refine session handling
- TA-93 Improve code robustness, security, and CI workflows
- **association**: TA-93 embed notification endpoints

### Perf

- **volunteer**: Use nested transactions for notifications
- TA-93 Enhance data validation, persistence, and type safety

## v0.2.0 (2026-01-10)

### Feat

- TA-124 Add MinIO object storage in compoes and update dev documentation
- Introduce performance benchmarks; enhance docs & CI
- TA-108 reporting endpoints added
- TA-108 volunteer mission engagement service
- TA-108 initial implementation of volunteer services
- TA-116 revert to previous lifespan order
- TA-116 domain exceptions for futur proofing
- TA-116 admins now have unique email
- TA-116 alembic script revision for user related new features
- TA-116 implemented crud for basic user (user and admin)
- TA-111 initial implementation of image storage logic
- TA-112 comprehensive implementation of database migration
- TA-112 alembic ini update for clarity
- TA-112 alembic initial installation
- TA-46 full database models basic implementation and auth logic
- TA-46 added full logging support
- TA-46 added minimal authentication logic
- TA-46 initial project structure

### Fix

- Correct volunteer creation benchmark and README
- Improve migration stability, error handling, and script validation
- update CORS origins format and fix broken README link
- TA-108 proper report type suggested by CodeRabbit
- TA-108 fixing favorite relationship
- TA-108 fixed typing for user related and volunteer email attribute
- TA-108 handle rare transaction race
- TA-108 type annotation order suggested by CodeRabbit
- TA-108 replaced session commit with flush for user related update logic
- TA-108 add one consistency check and its test (CodeRabbit)
- TA-108 using flush instead of commit for user update
- TA-116 more consistant exception params
- TA-116 phone for associations less restrictive limits
- TA-111 prevent file size from being equal to 0
- TA-111 file size calculation with clearer arguments
- TA-111 proper file size argument handling
- TA-111 security improvement for storage logic based on CodeRabbit
- TA-111 security improvement on storage logic based on CodeRabbit
- TA-111 main and storage util based on CodeRabbit
- TA-111 proper document storage logic
- TA-112 proper online defaults handling with alembic
- TA-112 improved comprehensiveness of init_db and alembic env
- TA-112 logging and env var fixes for intial db setup
- TA-112 application start logic fixes
- TA-113 fix settings based on CodeRabbit
- TA-113 corrected cors handling
- TA-46 environment telemetry distinction
- TA-46 db driver from url fixed
- TA-46 some code improvement based on coderabbit review

### Refactor

- Clarify OTLP configuration and remove unused env vars
- TA-116 import rewrite for consistency
- TA-116 exception message clarity
- TA-116 code improvement based on CodeRabbit suggestions
- TA-116 improved consistency for user related files
- TA-111 code improvements based on CodeRabbit
- TA-113 docker updates based on CodeRabbit
- TA-113 removed useless agent file
- TA-113 updated fastapi deployment commands
- TA-46 code update based on coderabbit
- TA-46 clarified security params and env vars
- TA-46 code improvement based on CodeRabbit
- TA-46 datetime field update based on CodeRabbit
- TA-46 improved code quality based on CodeRabbit
- TA-46 removed service user file
- TA-46 code refactor based on CodeRabbit suggestions
- TA-46 fixed lint with ruff
- TA-46 renamed validation function
- TA-46 removed favicon
- TA-46 added missing init filein app/core
- TA-46 moved tests folder
- TA-46 removed utils folder

### Perf

- TA-108 volunteer to public bulking for multiple retrieval
