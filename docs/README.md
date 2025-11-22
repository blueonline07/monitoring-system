# Documentation Index

Complete documentation for the monitoring system.

## 📚 Table of Contents

### Getting Started
- **[../README.md](../README.md)** - Main README with quick start guide

### Core Documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design patterns
- **[DATA_MODELS.md](DATA_MODELS.md)** - Complete data model reference
- **[STREAMING.md](STREAMING.md)** - Bidirectional streaming implementation

### Development
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development guide and best practices
- **[PROTOBUF.md](PROTOBUF.md)** - Protocol buffer generation guide
- **[TEST_FLOW.md](TEST_FLOW.md)** - Testing procedures

## 🎯 Quick Links

### For Users
Start with the [main README](../README.md) for installation and basic usage.

### For Developers
1. Read [ARCHITECTURE.md](ARCHITECTURE.md) for system overview
2. Check [DATA_MODELS.md](DATA_MODELS.md) for data structures
3. Follow [DEVELOPMENT.md](DEVELOPMENT.md) for contributing

### For Understanding
- **Architecture**: How components interact → [ARCHITECTURE.md](ARCHITECTURE.md)
- **Streaming**: How real-time communication works → [STREAMING.md](STREAMING.md)
- **Data**: What data flows through the system → [DATA_MODELS.md](DATA_MODELS.md)

## 📖 Document Descriptions

### ARCHITECTURE.md
- System components and responsibilities
- Module structure and dependencies
- Communication flows
- Design patterns used
- Configuration details

### DATA_MODELS.md
- Python data models (Pydantic)
- gRPC protocol buffers
- Kafka message schemas
- Usage examples
- Field descriptions

### STREAMING.md
- Bidirectional streaming architecture
- Protocol definition
- Implementation details
- Message flow examples
- Advantages over polling

### DEVELOPMENT.md
- Setup instructions
- Development workflow
- Adding new features
- Testing strategies
- Debugging tips
- Deployment options

### PROTOBUF.md
- Protocol buffer generation
- Fixing imports
- Regeneration commands

### TEST_FLOW.md
- Testing procedures
- Verification steps
- Troubleshooting

## 🔍 Finding Information

**"How do I..."**
- Install and run? → [README.md](../README.md)
- Add a new metric? → [DEVELOPMENT.md](DEVELOPMENT.md)
- Understand the architecture? → [ARCHITECTURE.md](ARCHITECTURE.md)
- Debug an issue? → [DEVELOPMENT.md](DEVELOPMENT.md)

**"What is..."**
- The data format? → [DATA_MODELS.md](DATA_MODELS.md)
- The streaming protocol? → [STREAMING.md](STREAMING.md)
- Each component's role? → [ARCHITECTURE.md](ARCHITECTURE.md)

**"Where is..."**
- The agent code? → `agent/agent.py`
- The server code? → `grpc_server/server.py`
- The data models? → `shared/models.py`
- The protocol definition? → `shared/monitoring.proto`

## 📝 Document Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| README.md | ✅ Current | Latest |
| ARCHITECTURE.md | ✅ Current | Latest |
| DATA_MODELS.md | ✅ Current | Latest |
| STREAMING.md | ✅ Current | Latest |
| DEVELOPMENT.md | ✅ Current | Latest |
| PROTOBUF.md | ✅ Current | Latest |
| TEST_FLOW.md | ✅ Current | Latest |

## 🤝 Contributing to Docs

To improve documentation:

1. Make changes to relevant markdown files
2. Keep examples up to date
3. Add screenshots if helpful
4. Test all commands/code snippets
5. Submit pull request

## 💡 Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams where helpful
- Keep table of contents updated
- Link between related documents

---

**Need help?** Create an issue or ask in discussions.

