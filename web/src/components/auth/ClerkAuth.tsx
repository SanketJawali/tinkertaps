import {
    ClerkLoaded,
    ClerkLoading,
    SignIn,
    SignUp,
} from '@clerk/astro/react';

interface ClerkAuthProps {
    mode: 'sign-in' | 'sign-up';
}

function AuthLoading() {
    return (
        <div className="w-full max-w-sm animate-pulse">
            <div className="rounded-xl border border-base-300 bg-base-100 p-6">
                <div className="h-10 rounded-md bg-base-200" />

                <div className="my-6 flex items-center gap-3">
                    <div className="h-px flex-1 bg-base-300" />
                    <div className="h-3 w-7 rounded bg-base-200" />
                    <div className="h-px flex-1 bg-base-300" />
                </div>

                <div className="space-y-5">
                    <div>
                        <div className="mb-2 h-3 w-12 rounded bg-base-200" />
                        <div className="h-10 rounded-md bg-base-200" />
                    </div>

                    <div>
                        <div className="mb-2 h-3 w-16 rounded bg-base-200" />
                        <div className="h-10 rounded-md bg-base-200" />
                    </div>

                    <div className="h-10 rounded-md bg-base-300" />
                </div>
            </div>
        </div>
    );
}

export default function ClerkAuth({ mode }: ClerkAuthProps) {
    return (
        <>
            <ClerkLoading>
                <AuthLoading />
            </ClerkLoading>

            <ClerkLoaded>
                {mode === 'sign-in' ? (
                    <SignIn
                        signUpUrl="/register"
                        fallbackRedirectUrl="/app"
                    />
                ) : (
                    <SignUp
                        signInUrl="/login"
                        fallbackRedirectUrl="/app"
                    />
                )}
            </ClerkLoaded>
        </>
    );
}
