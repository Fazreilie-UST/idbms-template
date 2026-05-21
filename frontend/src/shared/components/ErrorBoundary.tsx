import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button, Result } from "antd";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

/**
 * Catches render-time errors anywhere in its subtree and shows a friendly
 * fallback instead of leaking stack traces. Wraps the whole `<Routes>` so a
 * crash in any page can't blank the screen.
 *
 * Errors are logged to console (and could be sent to a monitoring backend)
 * but the rendered fallback never shows the underlying message to the user.
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Avoid leaking secrets via the message; this only goes to the dev console.
    // Hook a real reporting backend (e.g. Sentry) here if/when available.
    console.error("Unhandled UI error:", error, info?.componentStack);
  }

  handleReset = (): void => {
    // Soft-reload: clear the error state and navigate home.
    this.setState({ hasError: false });
    if (typeof window !== "undefined") {
      window.location.replace("/");
    }
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="Something went wrong"
          subTitle="The page hit an unexpected error. Please return to the dashboard and try again."
          extra={
            <Button type="primary" onClick={this.handleReset}>
              Back to home
            </Button>
          }
        />
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
