import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = {
  children: ReactNode
}

type State = {
  hasError: boolean
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Application render failure', error, errorInfo.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <main role="alert" className="mx-auto mt-16 max-w-xl rounded-2xl bg-white p-8 text-center shadow-lg">
          <h1 className="text-2xl font-bold text-slate-900">Something went wrong</h1>
          <p className="mt-3 text-slate-600">
            The page could not be displayed. Your saved analysis history has not been changed.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-6 rounded-lg bg-blue-600 px-5 py-3 font-semibold text-white hover:bg-blue-700"
          >
            Reload application
          </button>
        </main>
      )
    }

    return this.props.children
  }
}
