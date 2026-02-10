# Modern EMR Frontend

React + TypeScript frontend for the Modern EMR system.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file in the frontend directory with:
```
REACT_APP_API_URL=/api/v1
```

3. Start the development server:
```bash
npm start
```

The app will run on `http://localhost:3000` and proxy API requests to `http://localhost:8000`.

## Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm eject` - Eject from Create React App (irreversible)

## Project Structure

- `src/` - Source code
  - `api/` - API client functions
  - `components/` - React components
  - `contexts/` - React contexts (Auth, etc.)
  - `hooks/` - Custom React hooks
  - `pages/` - Page components
  - `styles/` - CSS modules
  - `types/` - TypeScript type definitions
  - `utils/` - Utility functions
