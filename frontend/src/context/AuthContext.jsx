import React, { createContext, useContext, useEffect, useState } from 'react';
import { auth, googleProvider } from '../firebase';
import {
    onAuthStateChanged,
    signInWithPopup,
    signOut,
    sendSignInLinkToEmail,
    isSignInWithEmailLink,
    signInWithEmailLink,
} from 'firebase/auth';

const AuthContext = createContext();

export const useAuth = () => {
    return useContext(AuthContext);
};

const EMAIL_LINK_KEY = 'emailForSignIn';

export const AuthProvider = ({ children }) => {
    const [currentUser, setCurrentUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // ── Google Sign-In ────────────────────────────────────────────────────────
    const loginWithGoogle = () => {
        return signInWithPopup(auth, googleProvider);
    };

    // ── Email Link (Passwordless) ─────────────────────────────────────────────
    /**
     * Sends a magic sign-in link to the given email address.
     * The link will return the user to the current page (/login) automatically.
     */
    const sendEmailLink = (email) => {
        const actionCodeSettings = {
            // URL the user will be redirected back to after clicking the link.
            // Must be in Firebase Console → Authorized Domains.
            url: window.location.origin + '/login',
            handleCodeInApp: true,
        };
        window.localStorage.setItem(EMAIL_LINK_KEY, email);
        return sendSignInLinkToEmail(auth, email, actionCodeSettings);
    };

    /**
     * Completes email-link sign-in when the user lands back on the page.
     * Reads the stored email from localStorage; if missing, prompts the user.
     * Returns the UserCredential on success.
     */
    const completeEmailLinkSignIn = async () => {
        if (!isSignInWithEmailLink(auth, window.location.href)) {
            return null; // Not an email-link URL — nothing to do
        }

        let email = window.localStorage.getItem(EMAIL_LINK_KEY);
        if (!email) {
            // Fallback: ask the user (different device / cleared storage)
            email = window.prompt('Please enter your email to complete sign-in:');
        }

        if (!email) throw new Error('Email is required to complete sign-in.');

        const result = await signInWithEmailLink(auth, email, window.location.href);
        window.localStorage.removeItem(EMAIL_LINK_KEY);
        return result;
    };

    // ── Shared ────────────────────────────────────────────────────────────────
    const logout = () => {
        return signOut(auth);
    };

    /** Returns a fresh Firebase ID token (JWT) for the current user. */
    const getIdToken = async () => {
        if (!auth.currentUser) throw new Error('Not authenticated');
        return auth.currentUser.getIdToken(/* forceRefresh */ false);
    };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            setCurrentUser(user);
            setLoading(false);
        });

        return unsubscribe;
    }, []);

    const value = {
        currentUser,
        loginWithGoogle,
        sendEmailLink,
        completeEmailLinkSignIn,
        logout,
        getIdToken,
    };

    return (
        <AuthContext.Provider value={value}>
            {!loading && children}
        </AuthContext.Provider>
    );
};
