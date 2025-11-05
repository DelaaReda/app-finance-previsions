import React from "react";

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error?: any }> {
  state = { error: undefined };
  
  static getDerivedStateFromError(error: any) { 
    return { error }; 
  }
  
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log the error to an error reporting service
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }
  
  render() {
    if (this.state.error) {
      return (
        <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
          <h2 className="text-xl font-bold text-red-700 mb-2">Un problème est survenu.</h2>
          <p className="text-red-600 mb-4">Essayez de rafraîchir. Si ça persiste, ouvrez /docs.</p>
          <button 
            onClick={() => window.location.reload()} 
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
          >
            Rafraîchir
          </button>
          <div className="text-xs text-gray-500 mt-3">
            {new Date().toLocaleString()} • ID: {Math.random().toString(36).substring(2, 8)}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}