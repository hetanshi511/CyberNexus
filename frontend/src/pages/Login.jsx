import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, ArrowRight, CheckCircle, Loader2 } from 'lucide-react';

/* ─── Google SVG icon ───────────────────────────────────────────────────── */
const GoogleIcon = () => (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.35-8.16 2.35-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
    </svg>
);

const Login = () => {
    const [email, setEmail]             = useState('');
    const [error, setError]             = useState('');
    const [linkLoading, setLinkLoading] = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);
    const [linkSent, setLinkSent]       = useState(false);
    const [completing, setCompleting]   = useState(false);

    const { loginWithGoogle, sendEmailLink, completeEmailLinkSignIn } = useAuth();
    const navigate = useNavigate();

    /* ── Auto-complete when user lands back from the email link ─────────── */
    useEffect(() => {
        const tryComplete = async () => {
            try {
                setCompleting(true);
                const result = await completeEmailLinkSignIn();
                if (result) navigate('/');
            } catch (err) {
                setError('Could not complete sign-in: ' + err.message);
            } finally {
                setCompleting(false);
            }
        };
        tryComplete();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    /* ── Send magic link ─────────────────────────────────────────────────── */
    const handleSendLink = async (e) => {
        e.preventDefault();
        if (!email.trim()) return;
        try {
            setError('');
            setLinkLoading(true);
            await sendEmailLink(email.trim());
            setLinkSent(true);
        } catch (err) {
            setError('Failed to send sign-in link: ' + err.message);
        } finally {
            setLinkLoading(false);
        }
    };

    /* ── Google sign-in ──────────────────────────────────────────────────── */
    const handleGoogleSignIn = async () => {
        try {
            setError('');
            setGoogleLoading(true);
            await loginWithGoogle();
            navigate('/');
        } catch (err) {
            setError('Failed to sign in with Google: ' + err.message);
            setGoogleLoading(false);
        }
    };

    /* ── Completing state ────────────────────────────────────────────────── */
    if (completing) {
        return (
            <div className="min-h-screen bg-[#f8fbff] flex items-center justify-center">
                <div className="text-center space-y-3">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-600" />
                    <p className="text-sm font-medium text-gray-500">Completing sign-in…</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#f8fbff] flex items-center justify-center px-4 pt-16">

            {/* Subtle background decoration */}
            <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
                <div className="absolute -top-32 -right-32 w-[480px] h-[480px] rounded-full bg-blue-100/50 blur-3xl" />
                <div className="absolute -bottom-32 -left-32 w-[400px] h-[400px] rounded-full bg-indigo-100/40 blur-3xl" />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: 'easeOut' }}
                className="relative w-full max-w-[420px]"
            >
                {/* Card */}
                <div className="bg-white rounded-2xl shadow-xl shadow-blue-100/60 border border-blue-100/80 overflow-hidden">

                    {/* Top gradient strip */}
                    <div className="h-1 w-full bg-gradient-to-r from-blue-500 to-indigo-500" />

                    <div className="px-8 py-10">

                        {/* Branding */}
                        <div className="flex items-center gap-3 mb-8">
                            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center flex-shrink-0">
                                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                                </svg>
                            </div>
                            <div>
                                <h1 className="text-[15px] font-bold text-gray-900 leading-tight">Invinsense</h1>
                                <p className="text-[11px] text-blue-500 font-medium tracking-wide uppercase">AI Marketplace</p>
                            </div>
                        </div>

                        {/* Heading */}
                        <div className="mb-8">
                            <h2 className="text-2xl font-bold text-gray-900 tracking-tight">Sign in</h2>
                            <p className="text-sm text-gray-500 mt-1">Access your security agent dashboard</p>
                        </div>

                        {/* Error */}
                        <AnimatePresence>
                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, y: -6 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0 }}
                                    className="mb-5 flex items-start gap-2 bg-red-50 border border-red-200 text-red-600 text-sm rounded-xl px-4 py-3"
                                >
                                    <span className="text-red-400 mt-0.5 flex-shrink-0">⚠</span>
                                    <span>{error}</span>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* ── Section 1 : Magic Link ─────────────────────────── */}
                        <div className="mb-5">
                            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-widest mb-3">
                                Passwordless sign-in
                            </p>

                            <AnimatePresence mode="wait">
                                {linkSent ? (
                                    /* Success state */
                                    <motion.div
                                        key="sent"
                                        initial={{ opacity: 0, scale: 0.97 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0 }}
                                        className="flex flex-col items-center gap-3 py-7 px-5 rounded-xl bg-blue-50 border border-blue-200 text-center"
                                    >
                                        <CheckCircle className="w-9 h-9 text-blue-600" strokeWidth={1.5} />
                                        <div>
                                            <p className="font-semibold text-gray-900 text-sm">Check your inbox</p>
                                            <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                                                A sign-in link was sent to{' '}
                                                <span className="font-medium text-blue-600">{email}</span>.
                                                <br />Click it to sign in — no password required.
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => { setLinkSent(false); setEmail(''); }}
                                            className="text-xs text-gray-400 hover:text-blue-600 underline underline-offset-2 transition-colors"
                                        >
                                            Use a different email
                                        </button>
                                    </motion.div>
                                ) : (
                                    /* Email form */
                                    <motion.form
                                        key="form"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        onSubmit={handleSendLink}
                                        className="space-y-3"
                                    >
                                        <div className="relative">
                                            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                                            <input
                                                id="email-link-input"
                                                type="email"
                                                required
                                                value={email}
                                                onChange={(e) => setEmail(e.target.value)}
                                                disabled={linkLoading}
                                                placeholder="name@company.com"
                                                className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl bg-gray-50 border border-gray-200 text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 transition-all disabled:opacity-60"
                                            />
                                        </div>
                                        <motion.button
                                            id="send-magic-link-btn"
                                            type="submit"
                                            disabled={linkLoading || !email.trim()}
                                            whileHover={{ scale: (linkLoading || !email.trim()) ? 1 : 1.01 }}
                                            whileTap={{ scale: (linkLoading || !email.trim()) ? 1 : 0.99 }}
                                            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold shadow-md shadow-blue-200 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                                        >
                                            {linkLoading ? (
                                                <>
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                    Sending link…
                                                </>
                                            ) : (
                                                <>
                                                    Send Link
                                                    <ArrowRight className="w-4 h-4" />
                                                </>
                                            )}
                                        </motion.button>
                                    </motion.form>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Divider */}
                        <div className="flex items-center gap-3 mb-5">
                            <div className="flex-1 h-px bg-gray-100" />
                            <span className="text-xs text-gray-400">or</span>
                            <div className="flex-1 h-px bg-gray-100" />
                        </div>

                        {/* ── Section 2 : Google ─────────────────────────────── */}
                        <motion.button
                            id="google-signin-btn"
                            onClick={handleGoogleSignIn}
                            disabled={googleLoading}
                            whileHover={{ scale: googleLoading ? 1 : 1.01 }}
                            whileTap={{ scale: googleLoading ? 1 : 0.99 }}
                            type="button"
                            className="w-full flex items-center justify-center gap-3 py-2.5 rounded-xl bg-white border border-gray-200 text-gray-700 text-sm font-semibold hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                            {googleLoading ? (
                                <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
                            ) : (
                                <GoogleIcon />
                            )}
                            Continue with Google
                        </motion.button>

                        {/* Footer */}
                        {/* <p className="text-center text-[11px] text-gray-400 mt-8">
                            By signing in you agree to our{' '}
                            <span className="text-blue-500 hover:text-blue-700 cursor-pointer transition-colors">Terms of Service</span>
                            {' '}and{' '}
                            <span className="text-blue-500 hover:text-blue-700 cursor-pointer transition-colors">Privacy Policy</span>.
                        </p> */}
                    </div>
                </div>
            </motion.div>
        </div>
    );
};

export default Login;
