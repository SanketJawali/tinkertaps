import { clerkMiddleware } from '@clerk/astro/server';

export const onRequest = clerkMiddleware({
    signInUrl: '/login',
    signUpUrl: '/register',
});
