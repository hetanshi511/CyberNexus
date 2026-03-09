import React, { useState } from 'react';
import { signInWithPopup, GoogleAuthProvider } from 'firebase/auth';
import { auth } from '../firebase';
import {
    CalendarDays, User, Mail, Briefcase, Loader2,
    CheckCircle, AlertCircle, Clock, Link as LinkIcon, CalendarCheck,
    ShieldCheck
} from 'lucide-react';

const SchedulerDashboard = () => {
    const [candidateName, setCandidateName] = useState('');
    const [candidateEmail, setCandidateEmail] = useState('');
    const [jobRole, setJobRole] = useState('');
    const [recruiterName, setRecruiterName] = useState('');
    const [recruiterEmail, setRecruiterEmail] = useState('');

    // OAuth state
    const [calendarToken, setCalendarToken] = useState(null);
    const [calendarConnected, setCalendarConnected] = useState(false);
    const [connectedEmail, setConnectedEmail] = useState('');

    const [isScheduling, setIsScheduling] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');

    const handleConnectCalendar = async () => {
        try {
            setError('');
            const provider = new GoogleAuthProvider();
            provider.addScope('https://www.googleapis.com/auth/calendar');
            provider.setCustomParameters({ prompt: 'consent' });

            const result = await signInWithPopup(auth, provider);
            const credential = GoogleAuthProvider.credentialFromResult(result);
            const token = credential?.accessToken;

            if (token) {
                setCalendarToken(token);
                setCalendarConnected(true);
                setConnectedEmail(result.user.email);
                // Auto-fill recruiter email and name from the Google account
                if (!recruiterEmail) setRecruiterEmail(result.user.email);
                if (!recruiterName) setRecruiterName(result.user.displayName || '');
            } else {
                setError('Could not retrieve calendar access token. Please try again.');
            }
        } catch (err) {
            console.error('Calendar OAuth Error:', err);
            if (err.code === 'auth/popup-closed-by-user') {
                setError('Authentication popup was closed. Please try again.');
            } else {
                setError(err.message || 'Failed to connect Google Calendar.');
            }
        }
    };

    const handleSchedule = async () => {
        if (!candidateName || !candidateEmail || !jobRole || !recruiterName) {
            setError('All fields are required.');
            return;
        }

        if (!calendarConnected) {
            setError('Please connect your Google Calendar first.');
            return;
        }

        setError('');
        setIsScheduling(true);
        setResult(null);

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${apiUrl}/api/scheduler-agent`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    candidate_name: candidateName,
                    candidate_email: candidateEmail,
                    job_role: jobRole,
                    recruiter_name: recruiterName,
                    recruiter_email: recruiterEmail,
                    calendar_access_token: calendarToken,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Scheduling failed.');
            }

            setResult(data);
        } catch (err) {
            console.error('Scheduler Error:', err);
            setError(err.message || 'An error occurred.');
        } finally {
            setIsScheduling(false);
        }
    };

    const handleReset = () => {
        setCandidateName('');
        setCandidateEmail('');
        setJobRole('');
        setRecruiterName('');
        setResult(null);
        setError('');
        // Keep calendar connected for scheduling multiple interviews
    };

    return (
        <div className="min-h-screen bg-[#f8fbff] p-6 lg:p-10 font-sans mt-16 pb-20">
            {/* Header */}
            <div className="max-w-4xl mx-auto mb-10">
                <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight flex items-center gap-3">
                    <CalendarDays className="w-10 h-10 text-violet-600" />
                    AI Interview Scheduler
                </h1>
                <p className="text-gray-500 mt-2 font-medium max-w-2xl">
                    Automatically schedule candidate interviews by finding the best available slot on the recruiter's calendar, generating a meeting link, and sending a confirmation email.
                </p>
            </div>

            {/* Form Section */}
            {!result && (
                <div className="max-w-4xl mx-auto space-y-6">
                    {/* Connect Google Calendar Card */}
                    <div className={`rounded-2xl shadow-sm border p-6 md:p-8 transition-all ${
                        calendarConnected
                            ? 'bg-emerald-50 border-emerald-200'
                            : 'bg-white border-gray-100'
                    }`}>
                        <div className="flex items-center justify-between flex-wrap gap-4">
                            <div>
                                <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2 mb-1">
                                    <CalendarCheck className={`w-5 h-5 ${calendarConnected ? 'text-emerald-600' : 'text-violet-500'}`} />
                                    {calendarConnected ? 'Google Calendar Connected' : 'Connect Recruiter\'s Google Calendar'}
                                </h3>
                                {calendarConnected ? (
                                    <p className="text-sm text-emerald-700 flex items-center gap-1.5">
                                        <ShieldCheck className="w-4 h-4" />
                                        Connected as <strong>{connectedEmail}</strong> — events will be created on this calendar
                                    </p>
                                ) : (
                                    <p className="text-sm text-gray-500">
                                        Sign in with the recruiter's Google account to read calendar availability and create events directly.
                                    </p>
                                )}
                            </div>
                            {!calendarConnected && (
                                <button
                                    id="connect-calendar-btn"
                                    onClick={handleConnectCalendar}
                                    className="px-6 py-2.5 bg-white border-2 border-gray-200 rounded-xl font-bold text-gray-700 hover:border-violet-300 hover:bg-violet-50 transition-all flex items-center gap-2 shrink-0"
                                >
                                    <svg className="w-5 h-5" viewBox="0 0 24 24">
                                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                                    </svg>
                                    Connect Google Calendar
                                </button>
                            )}
                            {calendarConnected && (
                                <button
                                    onClick={() => { setCalendarConnected(false); setCalendarToken(null); setConnectedEmail(''); }}
                                    className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 underline transition-all"
                                >
                                    Disconnect
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Form Fields */}
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Candidate Info */}
                            <div className="space-y-5">
                                <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2 mb-1">
                                    <User className="w-4 h-4 text-violet-500" />
                                    Candidate Information
                                </h3>
                                <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-1.5">
                                        Full Name <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        id="candidate-name"
                                        type="text"
                                        value={candidateName}
                                        onChange={(e) => setCandidateName(e.target.value)}
                                        placeholder="e.g. Rahul Sharma"
                                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-500 focus:outline-none transition-all text-gray-700"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-1.5">
                                        Email Address <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        id="candidate-email"
                                        type="email"
                                        value={candidateEmail}
                                        onChange={(e) => setCandidateEmail(e.target.value)}
                                        placeholder="e.g. rahul@gmail.com"
                                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-500 focus:outline-none transition-all text-gray-700"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-1.5">
                                        Job Role <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        id="job-role"
                                        type="text"
                                        value={jobRole}
                                        onChange={(e) => setJobRole(e.target.value)}
                                        placeholder="e.g. Backend Engineer"
                                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-500 focus:outline-none transition-all text-gray-700"
                                    />
                                </div>
                            </div>

                            {/* Recruiter Info */}
                            <div className="space-y-5">
                                <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2 mb-1">
                                    <Briefcase className="w-4 h-4 text-violet-500" />
                                    Recruiter Information
                                </h3>
                                <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-1.5">
                                        Recruiter Name <span className="text-red-500">*</span>
                                    </label>
                                    <input
                                        id="recruiter-name"
                                        type="text"
                                        value={recruiterName}
                                        onChange={(e) => setRecruiterName(e.target.value)}
                                        placeholder="e.g. Abinav Sridharan"
                                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-violet-500 focus:outline-none transition-all text-gray-700"
                                    />
                                </div>

                                {/* Rules Card */}
                                <div className="bg-violet-50 border border-violet-100 rounded-xl p-4 text-sm text-violet-800 space-y-1.5">
                                    <p className="font-bold text-xs uppercase tracking-wider text-violet-600">Scheduling Rules</p>
                                    <ul className="list-disc list-inside space-y-1 text-xs text-violet-700">
                                        <li>Working hours: 9 AM – 5 PM</li>
                                        <li>Monday to Friday only</li>
                                        <li>30-minute interview slots</li>
                                        <li>Max 4 meetings per day</li>
                                    </ul>
                                </div>
                            </div>
                        </div>

                        {error && (
                            <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 text-sm flex items-center gap-2">
                                <AlertCircle className="w-5 h-5 shrink-0" /> {error}
                            </div>
                        )}

                        <div className="mt-8 flex justify-end">
                            <button
                                id="schedule-btn"
                                onClick={handleSchedule}
                                disabled={isScheduling || !calendarConnected}
                                className="px-8 py-3 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-bold rounded-xl hover:from-violet-700 hover:to-indigo-700 transition-all shadow-lg shadow-violet-200 flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                            >
                                {isScheduling ? (
                                    <><Loader2 className="w-5 h-5 animate-spin" /> Scheduling...</>
                                ) : (
                                    <><CalendarCheck className="w-5 h-5" /> Schedule Interview</>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Loading State */}
            {isScheduling && (
                <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-sm border border-gray-100 p-12 flex flex-col items-center justify-center text-center">
                    <div className="relative mb-6">
                        <div className="w-20 h-20 rounded-full bg-violet-100 flex items-center justify-center">
                            <Loader2 className="w-10 h-10 text-violet-600 animate-spin" />
                        </div>
                        <div className="absolute -inset-1 rounded-full border-2 border-violet-200 animate-ping opacity-30"></div>
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Scheduling in Progress...</h3>
                    <p className="text-gray-500 max-w-md">
                        Checking recruiter calendar availability, finding the best slot, creating the event, and sending the confirmation email.
                    </p>
                </div>
            )}

            {/* Result Card */}
            {result && (
                <div className="max-w-4xl mx-auto space-y-6">
                    {/* Success Banner */}
                    <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 flex items-start gap-4">
                        <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                            <CheckCircle className="w-7 h-7 text-emerald-600" />
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-emerald-800 mb-1">Interview Scheduled Successfully!</h3>
                            <p className="text-sm text-emerald-700">
                                The interview has been added to the recruiter's calendar and a confirmation email has been sent to the candidate.
                            </p>
                        </div>
                    </div>

                    {/* Details Grid */}
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8">
                        <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
                            <CalendarDays className="w-5 h-5 text-violet-500" />
                            Interview Details
                        </h3>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-4">
                                <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Candidate</p>
                                    <p className="text-lg font-bold text-gray-900">{result.candidate_name}</p>
                                </div>
                                <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Scheduled Time</p>
                                    <p className="text-lg font-bold text-gray-900 flex items-center gap-2">
                                        <Clock className="w-5 h-5 text-violet-500" />
                                        {result.scheduled_time}
                                    </p>
                                </div>
                            </div>
                            <div className="space-y-4">
                                <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Meeting Link</p>
                                    <a
                                        href={result.meeting_link}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-base font-semibold text-blue-600 hover:underline flex items-center gap-2 break-all"
                                    >
                                        <LinkIcon className="w-4 h-4 shrink-0" />
                                        {result.meeting_link}
                                    </a>
                                </div>
                                <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                                    <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Calendar Event ID</p>
                                    <p className="text-sm font-mono text-gray-700 bg-gray-100 px-3 py-1.5 rounded-lg inline-block">
                                        {result.calendar_event_id || 'N/A'}
                                    </p>
                                </div>
                            </div>
                        </div>

                        {result.email_sent !== undefined && (
                            <div className={`mt-6 p-4 rounded-xl text-sm flex items-center gap-2 ${
                                result.email_sent
                                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                                    : 'bg-amber-50 text-amber-700 border border-amber-100'
                            }`}>
                                <Mail className="w-5 h-5 shrink-0" />
                                {result.email_sent
                                    ? 'Confirmation email sent to the candidate.'
                                    : 'Email was not sent (SMTP may not be configured).'}
                            </div>
                        )}
                    </div>

                    {/* Schedule Another */}
                    <div className="flex justify-center pt-2">
                        <button
                            id="schedule-another-btn"
                            onClick={handleReset}
                            className="px-8 py-3 bg-violet-600 text-white font-bold rounded-xl hover:bg-violet-700 transition-all shadow-md shadow-violet-200 flex items-center gap-2"
                        >
                            <CalendarCheck className="w-5 h-5" /> Schedule Another Interview
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SchedulerDashboard;
