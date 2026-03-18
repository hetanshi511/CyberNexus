import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * PrivateRoute — wraps a page component and redirects to /login if the user
 * is not authenticated via Firebase. Renders children once auth is resolved.
 */
const PrivateRoute = ({ children }) => {
    const { currentUser } = useAuth();
    return currentUser ? children : <Navigate to="/login" replace />;
};

export default PrivateRoute;
