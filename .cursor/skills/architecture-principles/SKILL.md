---
name: architecture-principles
description: Software architecture principles and design patterns. Used by arch-review for evaluations and by all agents when making design decisions or starting new features.
---

# Architecture Principles Skill

**Purpose**: Define architectural standards and design patterns for the project.

## When to Use

- **senior-reviewer** reads this skill before reviewing architecture
- **planner** reads when breaking down complex tasks
- **worker** reads when implementing new features or modules
- **reviewer** checks architectural consistency

---

## Core Principles

### 1. SOLID Principles

#### Single Responsibility Principle (SRP)
- One class/module = one reason to change
- Separate concerns (data, logic, presentation)

```typescript
// ✅ Good - Single responsibility
class UserRepository {
  async findById(id: string) { /* DB logic */ }
}

class UserService {
  validateUser(user: User) { /* Business logic */ }
}

// ❌ Bad - Multiple responsibilities
class User {
  async save() { /* DB logic */ }
  validate() { /* Business logic */ }
  render() { /* Presentation */ }
}
```

#### Open/Closed Principle (OCP)
- Open for extension, closed for modification
- Use interfaces, abstract classes, composition

#### Liskov Substitution Principle (LSP)
- Subtypes must be substitutable for base types
- Don't break parent class contracts

#### Interface Segregation Principle (ISP)
- Many specific interfaces > one general interface
- Clients shouldn't depend on unused methods

#### Dependency Inversion Principle (DIP)
- Depend on abstractions, not concretions
- High-level modules shouldn't depend on low-level modules

---

### 2. Separation of Concerns

#### Layered Architecture

```
┌─────────────────────────────┐
│   Presentation Layer        │  UI, Views, User Interface
├─────────────────────────────┤
│   Application Layer         │  Use Cases, Application Logic
├─────────────────────────────┤
│   Domain Layer              │  Business Logic, Entities
├─────────────────────────────┤
│   Data Layer                │  Data Access, Storage
├─────────────────────────────┤
│   Infrastructure Layer      │  External Services, I/O
└─────────────────────────────┘
```

**Rules:**
- Each layer only depends on layers below
- Business logic independent of infrastructure
- Easy to test each layer in isolation
- Upper layers depend on abstractions, not implementations

---

### 3. Design Patterns

#### Repository Pattern
Abstracts data access logic

```typescript
// Interface - defines what operations are available
interface UserRepository {
  findById(id: string): Promise<User>;
  save(user: User): Promise<void>;
  delete(id: string): Promise<void>;
}

// Implementation - concrete storage mechanism
class UserRepositoryImpl implements UserRepository {
  constructor(private storage: Storage) {}
  
  async findById(id: string): Promise<User> {
    return await this.storage.get('users', id);
  }
  
  async save(user: User): Promise<void> {
    await this.storage.set('users', user.id, user);
  }
}
```

#### Service Pattern
Encapsulates business logic

```typescript
class UserService {
  constructor(
    private userRepo: UserRepository,
    private notificationService: NotificationService
  ) {}

  async registerUser(data: RegisterDTO) {
    // 1. Validate input
    this.validateRegistrationData(data);
    
    // 2. Apply business rules
    const user = this.createUserFromDTO(data);
    
    // 3. Persist
    await this.userRepo.save(user);
    
    // 4. Trigger side effects
    await this.notificationService.sendWelcome(user);
    
    return user;
  }
}
```

#### Factory Pattern
Creates objects without specifying exact class

```typescript
class PaymentProcessorFactory {
  create(type: string): PaymentProcessor {
    switch(type) {
      case 'stripe': return new StripeProcessor();
      case 'paypal': return new PayPalProcessor();
      default: throw new Error('Unknown processor');
    }
  }
}
```

#### Strategy Pattern
Encapsulates algorithms, makes them interchangeable

```typescript
interface ValidationStrategy {
  validate(data: any): boolean;
}

class EmailValidation implements ValidationStrategy {
  validate(email: string): boolean { /* ... */ }
}

class PasswordValidation implements ValidationStrategy {
  validate(password: string): boolean { /* ... */ }
}
```

---

### 4. Dependency Injection

**Benefits:**
- Loose coupling
- Easy testing (mock dependencies)
- Flexible configuration

```typescript
// ✅ Good - DI via constructor
class UserController {
  constructor(
    private userService: UserService,
    private logger: Logger
  ) {}
}

// ❌ Bad - Hard dependencies
class UserController {
  private userService = new UserService();
  private logger = new ConsoleLogger();
}
```

---

### 5. Error Handling

#### Centralized Error Handling

```typescript
// Custom error types
class ValidationError extends Error {
  constructor(message: string, public field?: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

class NotFoundError extends Error {
  constructor(resource: string, id: string) {
    super(`${resource} with id ${id} not found`);
    this.name = 'NotFoundError';
  }
}

// Error handler example
class ErrorHandler {
  handle(error: Error): void {
    if (error instanceof ValidationError) {
      // Handle validation errors
    } else if (error instanceof NotFoundError) {
      // Handle not found errors
    } else {
      // Handle unexpected errors
    }
    
    this.log(error);
  }
  
  private log(error: Error): void {
    console.error(`[${error.name}]: ${error.message}`);
  }
}
```

---

### 6. Configuration Management

```typescript
// ✅ Good - Centralized config
export const config = {
  environment: process.env.NODE_ENV || 'development',
  
  storage: {
    type: process.env.STORAGE_TYPE || 'local',
    location: process.env.STORAGE_LOCATION,
  },
  
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    destination: process.env.LOG_DESTINATION || 'console',
  },
  
  features: {
    enableNotifications: process.env.ENABLE_NOTIFICATIONS === 'true',
    maxRetries: parseInt(process.env.MAX_RETRIES || '3'),
  }
};

// ❌ Bad - Scattered configuration
const storageType = process.env.STORAGE_TYPE; // in storage file
const logLevel = process.env.LOG_LEVEL; // in logger file
const maxRetries = process.env.MAX_RETRIES; // in retry logic
```

---

## Code Organization

### Feature-Based Structure
Best for large applications where features are relatively independent

```
src/
├── features/
│   ├── authentication/
│   │   ├── auth.service.ts
│   │   ├── auth.store.ts
│   │   ├── auth.types.ts
│   │   └── auth.utils.ts
│   ├── users/
│   │   ├── user.service.ts
│   │   ├── user.types.ts
│   │   └── user.utils.ts
│   └── notifications/
├── shared/
│   ├── components/
│   ├── utils/
│   └── types/
└── config/
```

**Advantages:**
- Features are self-contained
- Easy to find related code
- Can scale teams by feature
- Easy to remove/add features

### Layer-Based Structure
Best for smaller applications or when layers are more important than features

```
src/
├── services/
├── repositories/
├── models/
├── utils/
└── types/
```

**Advantages:**
- Clear technical boundaries
- Easier to enforce layer rules
- Good for smaller codebases
- Simple to understand

---

## Performance Principles

### 1. Data Access
- Index frequently accessed data
- Implement pagination for large datasets
- Use connection pooling for external resources
- Avoid N+1 queries (fetch related data efficiently)
- Lazy load data when appropriate

### 2. Caching
- Cache expensive computations
- Use appropriate cache invalidation strategies
- Consider memory vs speed tradeoffs
- Cache at the right layer (application, data, CDN)

### 3. Async Operations
- Use async/await for I/O operations
- Don't block the main thread
- Implement background jobs for heavy tasks
- Use queues/streams for decoupling
- Consider parallelization opportunities

### 4. Resource Management
- Clean up resources (connections, file handles, timers)
- Implement proper timeout mechanisms
- Use object pooling for expensive resources
- Monitor memory usage and prevent leaks

---

## Testing Strategy

### Test Pyramid

```
        /\
       /  \    E2E Tests (few)
      /----\
     /      \  Integration Tests (some)
    /--------\
   /          \ Unit Tests (many)
  /____________\
```

### What to Test:
- **Unit**: Business logic, utilities, pure functions, algorithms
- **Integration**: Component interactions, data flow, external services
- **E2E**: Critical user flows, main scenarios

---

## Anti-Patterns to Avoid

### ❌ God Object
One class that knows/does too much

### ❌ Spaghetti Code
Tangled, unstructured code with unclear flow

### ❌ Magic Numbers
Hardcoded values without explanation
```typescript
// ❌ Bad
if (user.age > 18) { /* ... */ }

// ✅ Good
const MINIMUM_AGE = 18;
if (user.age > MINIMUM_AGE) { /* ... */ }
```

### ❌ Circular Dependencies
Module A depends on B, B depends on A

### ❌ Premature Optimization
Optimizing before identifying actual bottlenecks

---

## Architecture Review Checklist

When reviewing architecture:

### Structure
- [ ] Clear separation of concerns
- [ ] Consistent folder structure
- [ ] Logical module boundaries

### Dependencies
- [ ] No circular dependencies
- [ ] Dependency injection used
- [ ] Abstractions over concretions

### Scalability
- [ ] Components/services are stateless where possible
- [ ] Data access is optimized (indexed, cached)
- [ ] Resource usage is efficient
- [ ] System can handle increased load

### Maintainability
- [ ] Code is self-documenting
- [ ] Consistent naming conventions
- [ ] Easy to add new features

### Testability
- [ ] Business logic isolated
- [ ] Dependencies can be mocked
- [ ] Test coverage adequate

---

## When to Refactor Architecture

Signs you need architectural changes:

1. **Adding features is increasingly difficult**
2. **Changes in one area break unrelated areas**
3. **Tests are hard to write or brittle**
4. **Code duplication everywhere**
5. **Performance issues at scale**

---

## References

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Design Patterns: Elements of Reusable Object-Oriented Software](https://en.wikipedia.org/wiki/Design_Patterns)

---

**Note**: This skill should be consulted by agents when making architectural decisions or reviewing system design.
