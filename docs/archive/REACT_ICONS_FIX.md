# React Icons Type Errors Fix

## Issue
React Icons components showing as invalid JSX components due to TypeScript type compatibility.

## Solution Options

### Option 1: Type Assertion (Quick Fix)
Add type assertions to icon components:
```typescript
{isLocked && <FaLock className={styles.lockIcon} as any />}
```

### Option 2: Update TypeScript Config
Add to `tsconfig.json`:
```json
{
  "compilerOptions": {
    "jsx": "react-jsx",
    "skipLibCheck": true
  }
}
```

### Option 3: Use Icon Components Differently
Instead of direct JSX, use as function:
```typescript
const LockIcon = FaLock;
{isLocked && <LockIcon className={styles.lockIcon} />}
```

## Recommended Fix
Update `tsconfig.json` to include `"skipLibCheck": true` to skip type checking of declaration files.

