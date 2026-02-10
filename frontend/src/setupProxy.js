/**
 * Setup proxy for React development server
 * 
 * This file is automatically loaded by react-scripts and configures
 * the proxy to forward API requests to the Django backend.
 * 
 * IMPORTANT: Restart the React dev server after modifying this file!
 */
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Proxy all /api requests to Django backend
  // When using app.use('/api', ...), Express strips /api from req.url
  // So we need to add it back using pathRewrite function
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false,
      logLevel: 'info',
      timeout: 30000, // 30 second timeout
      proxyTimeout: 30000, // 30 second proxy timeout
      // Add /api back to the path since Express strips it when using app.use('/api', ...)
      // req.url will be '/v1/auth/login/' but we need '/api/v1/auth/login/'
      pathRewrite: function (path, req) {
        // path is already stripped of /api by Express (e.g., '/v1/auth/login/')
        // We need to add /api back: '/api/v1/auth/login/'
        const rewrittenPath = '/api' + path;
        if (process.env.NODE_ENV === 'development') {
          console.log(`[PROXY PATH REWRITE] ${path} -> ${rewrittenPath}`);
        }
        return rewrittenPath;
      },
      onProxyReq: (proxyReq, req, res) => {
        if (process.env.NODE_ENV === 'development') {
          console.log(`[PROXY REQ] ${req.method} ${req.originalUrl || req.url} -> http://localhost:8000${proxyReq.path}`);
        }
      },
      onProxyRes: (proxyRes, req, res) => {
        if (process.env.NODE_ENV === 'development') {
          const originalPath = req.originalUrl || req.url;
          console.log(`[PROXY RES] ${req.method} ${originalPath} <- ${proxyRes.statusCode}`);
        }
      },
      onError: (err, req, res) => {
        const originalPath = req.originalUrl || req.url;
        console.error(`[PROXY ERROR] ${req.method} ${originalPath}:`, err.message);
        
        // Provide more helpful error messages
        let errorMessage = 'Proxy error: ' + err.message;
        if (err.code === 'ECONNREFUSED') {
          errorMessage = 'Backend server is not running. Please start the Django backend server on port 8000.';
        } else if (err.code === 'ETIMEDOUT') {
          errorMessage = 'Backend server is not responding. Please check if the server is running and accessible.';
        }
        
        if (!res.headersSent) {
          res.writeHead(504, {
            'Content-Type': 'application/json',
          });
          res.end(JSON.stringify({
            error: errorMessage,
            code: err.code,
            details: 'Make sure the Django backend is running: cd backend && python manage.py runserver'
          }));
        }
      },
    })
  );
  
  if (process.env.NODE_ENV === 'development') {
    console.log('[PROXY] Configured: /api -> http://localhost:8000 (adding /api prefix back)');
  }
};
