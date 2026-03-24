import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import PrivateRoute from './components/PrivateRoute';
import Home from './pages/Home';
import SearchPage from './pages/SearchPage';
import AgentDetails from './pages/AgentDetails';
import Login from './pages/Login';
import ComplianceDashboard from './pages/ComplianceDashboard';
import ContentReviewDashboard from './pages/ContentReviewDashboard';
import HeaderValidatorDashboard from './pages/HeaderValidatorDashboard';
import ResumeReviewerDashboard from './pages/ResumeReviewerDashboard';
import SchedulerDashboard from './pages/SchedulerDashboard';
import EmailSecurityDashboard from './pages/EmailSecurityDashboard';
import PPTGeneratorDashboard from './pages/PPTGeneratorDashboard';
import { AuthProvider } from './context/AuthContext';

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="min-h-screen font-sans bg-[#f8fbff] selection:bg-blue-100 selection:text-blue-900 flex flex-col">
          <Navbar />
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<Home />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/agent/:id" element={<AgentDetails />} />
            <Route path="/login" element={<Login />} />

            {/* Protected routes — require Firebase login */}
            <Route path="/compliance-dashboard" element={<PrivateRoute><ComplianceDashboard /></PrivateRoute>} />
            <Route path="/content-review-dashboard" element={<PrivateRoute><ContentReviewDashboard /></PrivateRoute>} />
            <Route path="/header-validator-dashboard" element={<PrivateRoute><HeaderValidatorDashboard /></PrivateRoute>} />
            <Route path="/resume-reviewer-dashboard" element={<PrivateRoute><ResumeReviewerDashboard /></PrivateRoute>} />
            <Route path="/scheduler-dashboard" element={<PrivateRoute><SchedulerDashboard /></PrivateRoute>} />
            <Route path="/email-security-dashboard" element={<PrivateRoute><EmailSecurityDashboard /></PrivateRoute>} />
            <Route path="/ppt-generator-dashboard" element={<PrivateRoute><PPTGeneratorDashboard /></PrivateRoute>} />
          </Routes>
          <Footer />
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;
