# Express.js Server

Node.js/TypeScript REST API server for Snow Analytics Stock Platform.

## Tech Stack
- Node.js
- Express.js
- TypeScript
- Zod (validation)

## Structure
```
expressjs-server/
├── src/
│   ├── api/              # Controllers, routes, middlewares
│   ├── core/             # Business logic (services, interfaces)
│   ├── infrastructure/   # External dependencies (DB, APIs)
│   ├── types/            # TypeScript type definitions
│   ├── utils/            # Utilities
│   └── index.ts          # Entry point
├── package.json
├── tsconfig.json
└── README.md
```

## Getting Started

### Install dependencies
```bash
npm install
```

### Run development server
```bash
npm run dev
```

### Build for production
```bash
npm run build
npm start
```

## Environment Variables
Copy `.env.example` to `.env` and configure:
```
PORT=5000
NODE_ENV=development
PYTHON_API_URL=http://localhost:8000
```

## API Documentation
Available at: `http://localhost:5000/api/health`
