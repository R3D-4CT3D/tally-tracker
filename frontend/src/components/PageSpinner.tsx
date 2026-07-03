export function PageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-linen dark:bg-charcoal">
      <div
        className="h-8 w-8 animate-spin rounded-full border-2 border-ember border-t-transparent motion-reduce:animate-none"
        role="status"
        aria-label="Loading"
      />
    </div>
  );
}
