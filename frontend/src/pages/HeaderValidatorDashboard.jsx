import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Printer, AlertCircle, Mail, Loader2, Check } from 'lucide-react';
import HeaderValidatorReport from '../components/HeaderValidatorReport';

const HeaderValidatorDashboard = () => {
    const [report, setReport] = useState(null);
    const [email, setEmail] = useState('');
    const [isSendingEmail, setIsSendingEmail] = useState(false);
    const [emailSuccess, setEmailSuccess] = useState(false);
    const [emailError, setEmailError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        const storedReport = localStorage.getItem('latest_header_report');
        if (storedReport) {
            try {
                setReport(JSON.parse(storedReport));
            } catch (e) {
                console.error("Failed to parse report", e);
            }
        }
    }, []);

    if (!report) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center bg-white p-8 rounded-2xl shadow-sm border border-gray-100 max-w-md">
                    <AlertCircle className="w-12 h-12 text-blue-500 mx-auto mb-4" />
                    <h2 className="text-2xl font-bold text-gray-800 mb-2">No Report Found</h2>
                    <p className="text-gray-500 mb-6 leading-relaxed">Please run the Header Validator Agent first to generate a structured security analysis report.</p>
                    <button 
                        onClick={() => navigate('/agent/header-validator')}
                        className="w-full px-4 py-3 bg-blue-600 font-semibold text-white rounded-xl hover:bg-blue-700 transition-colors shadow-md shadow-blue-200"
                    >
                        Go to Header Validator
                    </button>
                </div>
            </div>
        );
    }

    const handleSendEmail = async () => {
        if (!email) {
            setEmailError('Please enter a valid email address.');
            return;
        }

        setIsSendingEmail(true);
        setEmailError('');
        setEmailSuccess(false);

        try {
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const payload = {
                to_email: email, 
                dashboard_route: "/header-validator-dashboard",
                report_data: report
            };

            const response = await fetch(`${apiUrl}/api/generate_and_mail_pdf`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload),
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Failed to generate PDF on the server.');
            }

            // We no longer download the PDF locally. The backend has emailed it.
            setEmailSuccess(true);
            setTimeout(() => setEmailSuccess(false), 5000);
        } catch(err) {
            console.error('PDF Generation Error:', err);
            setEmailError('PDF Error: ' + (err.message || String(err)));
        } finally {
            setIsSendingEmail(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#f8fbff] p-6 lg:p-10 font-sans mt-16">
            {/* Header */}
            <div className="max-w-7xl mx-auto mb-10 flex flex-col md:flex-row md:items-center justify-between gap-6 print:hidden">
                <style>{`
                    @media print {
                        body * { visibility: hidden; }
                        #printable-report, #printable-report * { visibility: visible; }
                        #printable-report { position: absolute; left: 0; top: 0; width: 100%; margin: 0; padding: 0; border: none; }
                        @page { margin: 1cm; size: portrait; }
                        .no-print { display: none !important; }
                    }
                `}</style>
                <div>
                    <button 
                        onClick={() => navigate('/agent/header-validator')}
                        className="flex items-center gap-2 text-sm text-gray-500 hover:text-blue-600 transition-colors mb-2 font-medium"
                    >
                        <ArrowLeft className="w-4 h-4" /> Back to Agent
                    </button>
                    <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight">Security Header Report</h1>
                    <p className="text-gray-500 mt-1 font-medium">Domain Security Analysis • {new Date().toLocaleDateString()}</p>
                </div>
                
                {/* Action Buttons & Email Input */}
                <div className="flex flex-col sm:flex-row gap-3 items-end sm:items-center">
                    <div className="flex items-center space-x-2 bg-white p-1 rounded-xl border border-gray-200 shadow-sm">
                        <input 
                            type="email" 
                            placeholder="Email report to..." 
                            value={email}
                            onChange={(e) => { setEmail(e.target.value); setEmailError(''); }}
                            className="px-3 py-2 text-sm outline-none bg-transparent w-48 sm:w-64"
                        />
                        <button 
                            onClick={handleSendEmail}
                            disabled={isSendingEmail}
                            className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white rounded-lg transition-all ${
                                emailSuccess ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'
                            } disabled:opacity-50`}
                        >
                            {isSendingEmail ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : emailSuccess ? (
                                <><Check className="w-4 h-4" /> Sent</>
                            ) : (
                                <><Mail className="w-4 h-4" /> Send PDF</>
                            )}
                        </button>
                    </div>

                    <button 
                        onClick={() => window.print()}
                        className="flex items-center gap-2 px-5 py-[10px] bg-white border border-gray-200 rounded-xl text-gray-700 hover:bg-gray-50 font-semibold shadow-sm transition-all"
                    >
                        <Printer className="w-4 h-4" />
                        Print
                    </button>
                </div>
            </div>
            
            {emailError && (
                <div className="max-w-7xl mx-auto mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 text-sm flex items-center gap-2 print:hidden">
                    <AlertCircle className="w-4 h-4" /> {emailError}
                </div>
            )}

            <style>{`
                /* Override Tailwind v4 OKLCH variables with HEX fallbacks specifically for html2canvas compatibility */
                #printable-report {
                    --color-white: #ffffff;
                    --color-black: #000000;
                    --color-gray-50: #f9fafb;
                    --color-gray-100: #f3f4f6;
                    --color-gray-200: #e5e7eb;
                    --color-gray-300: #d1d5db;
                    --color-gray-400: #9ca3af;
                    --color-gray-500: #6b7280;
                    --color-gray-600: #4b5563;
                    --color-gray-700: #374151;
                    --color-gray-800: #1f2937;
                    --color-gray-900: #111827;
                    --color-blue-50: #eff6ff;
                    --color-blue-100: #dbeafe;
                    --color-blue-500: #3b82f6;
                    --color-blue-600: #2563eb;
                    --color-blue-700: #1d4ed8;
                    --color-blue-800: #1e40af;
                    --color-green-50: #f0fdf4;
                    --color-green-100: #dcfce7;
                    --color-green-400: #4ade80;
                    --color-green-500: #22c55e;
                    --color-green-600: #16a34a;
                    --color-green-700: #15803d;
                    --color-green-800: #166534;
                    --color-red-50: #fef2f2;
                    --color-red-100: #fee2e2;
                    --color-red-400: #f87171;
                    --color-red-500: #ef4444;
                    --color-red-600: #dc2626;
                    --color-red-700: #b91c1c;
                    --color-red-800: #991b1b;
                    --color-orange-50: #fff7ed;
                    --color-orange-100: #ffedd5;
                    --color-orange-500: #f97316;
                    --color-orange-600: #ea580c;
                    --color-orange-800: #9a3412;
                    --color-teal-50: #f0fdfa;
                    --color-teal-100: #ccfbf1;
                    --color-teal-500: #14b8a6;
                    --color-teal-600: #0d9488;
                    --color-teal-700: #0f766e;
                    --color-purple-50: #faf5ff;
                    --color-purple-100: #f3e8ff;
                    --color-purple-600: #9333ea;
                    --color-purple-700: #7e22ce;
                    --color-pink-50: #fdf2f8;
                    --color-pink-100: #fce7f3;
                    --color-pink-700: #be185d;
                    --color-emerald-50: #ecfdf5;
                    --color-emerald-100: #d1fae5;
                    --color-emerald-700: #047857;
                }
                #printable-report * {
                    text-shadow: none !important;
                    box-shadow: none !important;
                }
            `}</style>
            <div id="printable-report" className="max-w-7xl mx-auto space-y-8 pb-10">
                <HeaderValidatorReport report={report} />
            </div>
        </div>
    );
};

export default HeaderValidatorDashboard;
