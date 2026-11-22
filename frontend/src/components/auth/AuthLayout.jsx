export const AuthLayout = ({ children, aside }) => (
  <div className="min-h-screen bg-background lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
    <div className="flex items-start justify-center px-5 py-10 sm:px-10 lg:items-center lg:py-16">
      <div className="w-full max-w-[400px] animate-fade-up">{children}</div>
    </div>
    {aside && (
      <div className="border-t border-border bg-sidebar px-5 py-10 sm:px-10 lg:flex lg:items-center lg:border-l lg:border-t-0 lg:py-16">
        <div className="mx-auto w-full max-w-[440px] animate-fade-up">{aside}</div>
      </div>
    )}
  </div>
);
