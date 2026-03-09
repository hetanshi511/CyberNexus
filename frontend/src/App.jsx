import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import SearchPage from './pages/SearchPage';
import AgentDetails from './pages/AgentDetails';
import Login from './pages/Login';
import ComplianceDashboard from './pages/ComplianceDashboard';
import ContentReviewDashboard from './pages/ContentReviewDashboard';
import HeaderValidatorDashboard from './pages/HeaderValidatorDashboard';
import ResumeReviewerDashboard from './pages/ResumeReviewerDashboard';
import SchedulerDashboard from './pages/SchedulerDashboard';
import { AuthProvider } from './context/AuthContext';

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="min-h-screen font-sans bg-[#f8fbff] selection:bg-blue-100 selection:text-blue-900 flex flex-col">
          <Navbar />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/agent/:id" element={<AgentDetails />} />
            <Route path="/compliance-dashboard" element={<ComplianceDashboard />} />
            <Route path="/content-review-dashboard" element={<ContentReviewDashboard />} />
            <Route path="/header-validator-dashboard" element={<HeaderValidatorDashboard />} />
            <Route path="/resume-reviewer-dashboard" element={<ResumeReviewerDashboard />} />
            <Route path="/scheduler-dashboard" element={<SchedulerDashboard />} />
            <Route path="/login" element={<Login />} />
          </Routes>
          <Footer />
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;
