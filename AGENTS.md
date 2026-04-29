# AI Knowledge Platform - Agent Guidelines

This document provides coding conventions and build commands for agentic coding agents working in this repository.

## Project Overview

This is a multi-service project consisting of:
- **java-service/**: Java backend service using BladeX framework (Spring Boot 3.x, Java 17)
- **python-ai-service/**: Python AI service using FastAPI, LangChain, LangGraph, Milvus

---

## Build/Lint/Test Commands

### Java Service (java-service/)

```bash
# Build project
mvn clean package

# Build without running tests
mvn clean package -DskipTests

# Run all tests
mvn test

# Run a single test class
mvn test -Dtest=BladeTest

# Run a single test method
mvn test -Dtest=BladeTest#contextLoads

# Run the application
mvn spring-boot:run

# Install dependencies
mvn clean install
```

### Python Service (python-ai-service/)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn main:app --host 0.0.0.0 --port 8000

# Run with auto-reload (development)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run all tests
pytest

# Run a single test file
pytest tests/test_file.py

# Run a single test function
pytest tests/test_file.py::test_function_name

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=. --cov-report=term-missing
```

---

## Code Style Guidelines

### Java Service Conventions

#### Package Structure
- Base package: `org.springblade`
- Modules under: `org.springblade.modules.{module_name}`
- Common utilities: `org.springblade.common`
- Test classes: `org.springblade.test`

#### Naming Conventions
- **Service Interface**: `IXxxService` (e.g., `IUserService`)
- **Service Implementation**: `XxxServiceImpl` (e.g., `UserServiceImpl`)
- **Controller**: `XxxController` (e.g., `UserController`)
- **Entity**: `Xxx` (e.g., `User`, extends `TenantEntity`)
- **VO (View Object)**: `XxxVO` (e.g., `UserVO`)
- **Wrapper**: `XxxWrapper` (e.g., `UserWrapper`)
- **Mapper**: `XxxMapper` (e.g., `UserMapper`)

#### Imports Order
1. Java standard library
2. Third-party libraries (Spring, MyBatis-Plus, Lombok)
3. BladeX framework imports
4. Project-specific imports

#### Annotations
- Use Lombok: `@Data`, `@AllArgsConstructor`, `@EqualsAndHashCode`
- Service layer: `@Service`
- Controller: `@RestController`, `@RequestMapping`
- Permission: `@PreAuth(RoleConstant.HAS_ROLE_ADMIN)`
- Transaction: `@Transactional(rollbackFor = Exception.class)`

#### Code Style
- 4-space indentation (tabs in existing code)
- Javadoc comments for public classes and methods
- BladeX license header at the top of each file
- Use `@Serial` annotation for serialVersionUID

#### Error Handling
- Use `ServiceException` for business logic errors
- Use `R<T>` as standard API response wrapper
- Example: `return R.data(userVO);` or `return R.fail("error message");`

---

### Python Service Conventions

#### Directory Structure
```
python-ai-service/
├── api/            # FastAPI route handlers
├── models/         # Pydantic models
├── service/        # Business logic services
├── middleware/     # Authentication middleware
├── workflows/      # LangGraph workflow definitions
├── utils/          # Utility functions
├── config.py       # Centralized configuration
└── main.py         # FastAPI application entry
```

#### Naming Conventions
- **Files**: snake_case (e.g., `auth_service.py`)
- **Classes**: PascalCase (e.g., `TokenCache`, `ChatRequest`)
- **Functions/Variables**: snake_case (e.g., `validate_token`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `REDIS_URL`)
- **Private module variables**: Prefix with underscore (e.g., `_checkpointer`)

#### Imports Order
1. Standard library (e.g., `os`, `json`, `asyncio`)
2. Third-party libraries (e.g., `fastapi`, `httpx`, `langchain`)
3. Local modules (e.g., `from config import ...`)

#### Type Hints
- Use Python 3.10+ syntax: `list[dict]`, `dict[str, Any]`, `X | None`
- Use `TypedDict` for complex state structures
- Use `Annotated` for LangGraph reducers

#### Code Style
- 4-space indentation
- Docstrings in Chinese (triple-quoted)
- Module-level singletons for expensive resources (LLM, Milvus connections)
- Async functions for I/O operations
- Early return pattern for error handling

#### Error Handling
- Use try/except with specific exception types
- Log errors with context
- Graceful degradation (e.g., fallback to minimum permissions)
- Example pattern:
```python
try:
    response = await client.get(url)
    response.raise_for_status()
except httpx.TimeoutException:
    logger.warning("Request timeout")
    return fallback_value
```

#### Configuration
- All environment variables in `config.py`
- Use `python-dotenv` for `.env` loading
- Write required values to `os.environ` for LangChain compatibility

---

## Framework-Specific Patterns

### BladeX (Java)
- Use `BladeUser` for authenticated user context via `AuthUtil.getUser()`
- Use `@PreAuth` for role-based access control
- Use `R<T>` for API responses: `R.data()`, `R.fail()`, `R.success()`
- Use `Condition.getQueryWrapper()` for query building
- Use `Kv` for flexible key-value data

### LangChain/LangGraph (Python)
- Define state with `TypedDict` and `Annotated`
- Use `StateGraph` for workflow definition
- Use checkpointer for conversation memory
- Use `astream_events` for streaming responses

---

## Important Files

| File | Purpose |
|------|---------|
| `java-service/pom.xml` | Maven dependencies and build config |
| `python-ai-service/requirements.txt` | Python dependencies |
| `python-ai-service/config.py` | Environment configuration |
| `python-ai-service/.env.example` | Environment variables template |

---

## Notes for Agents

1. **Never commit `.env` files** - They contain secrets
2. **Use existing patterns** - Follow the code style in neighboring files
3. **Chinese comments acceptable** - This is a Chinese-language project
4. **Java files have BladeX license headers** - Preserve them when editing
5. **Python uses module-level singletons** - Avoid recreating connections per request
6. **Permission checks are critical** - Use `@PreAuth` in Java, `access_levels` in Python