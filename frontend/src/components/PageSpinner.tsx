export function PageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface">
      <div
        className="h-8 w-8 animate-spin rounded-full border-2 border-green-500 border-t-transparent motion-reduce:animate-none"
        role="status"
        aria-label="Loading"
      />
    </div>
  );
}
