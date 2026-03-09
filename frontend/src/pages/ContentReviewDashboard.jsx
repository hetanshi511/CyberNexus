import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Printer, Download, CheckCircle, AlertCircle, FileText, AlertTriangle, Mail, Loader2, Check } from 'lucide-react';

const ContentReviewDashboard = () => {
    const [report, setReport] = useState(null);
    const [email, setEmail] = useState('');
    const [isSendingEmail, setIsSendingEmail] = useState(false);
    const [emailSuccess, setEmailSuccess] = useState(false);
    const [emailError, setEmailError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        const storedReport = localStorage.getItem('latest_content_review_report');
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
                    <AlertCircle className="w-12 h-12 text-teal-500 mx-auto mb-4" />
                    <h2 className="text-2xl font-bold text-gray-800 mb-2">No Report Found</h2>
                    <p className="text-gray-500 mb-6 leading-relaxed">Please run the Content Reviewer Agent first to generate a structured content analysis report.</p>
                    <button 
                        onClick={() => navigate('/agent/content-reviewer')}
                        className="w-full px-4 py-3 bg-teal-600 font-semibold text-white rounded-xl hover:bg-teal-700 transition-colors shadow-md shadow-teal-200"
                    >
                        Go to Content Reviewer
                    </button>
                </div>
            </div>
        );
    }

    const { summary, pages } = report;

    const downloadCSV = () => {
        if (!pages || pages.length === 0) return;
        const headers = ['URL', 'Type', 'Original Text', 'Suggested Correction', 'Explanation'];
        const csvRows = [headers.join(',')];
        
        pages.forEach(page => {
            if (page.errors && page.errors.length > 0) {
                page.errors.forEach(err => {
                    const values = [
                        `"${page.url}"`,
                        err.type || 'unknown',
                        `"${(err.original_text || '').replace(/"/g, '""')}"`,
                        `"${(err.suggested_correction || '').replace(/"/g, '""')}"`,
                        `"${(err.explanation || '').replace(/"/g, '""')}"`
                    ];
                    csvRows.push(values.join(','));
                });
            } else {
                csvRows.push([`"${page.url}"`, 'None', 'None', 'None', 'No errors found'].join(','));
            }
        });
        
        const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `content_review_report_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    };

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
                dashboard_route: "/content-review-dashboard",
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
                        onClick={() => navigate('/agent/content-reviewer')}
                        className="flex items-center gap-2 text-sm text-gray-500 hover:text-teal-600 transition-colors mb-2 font-medium"
                    >
                        <ArrowLeft className="w-4 h-4" /> Back to Agent
                    </button>
                    <h1 className="text-3xl md:text-4xl font-bold text-gray-900 tracking-tight">Content Quality Report</h1>
                    <p className="text-gray-500 mt-1 font-medium">Automated Proofreading Analysis • {new Date().toLocaleDateString()}</p>
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
                                emailSuccess ? 'bg-green-600 hover:bg-green-700' : 'bg-teal-600 hover:bg-teal-700'
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
                    <button onClick={downloadCSV} className="flex items-center gap-2 px-5 py-[10px] bg-teal-600 text-white rounded-xl hover:bg-teal-700 font-semibold shadow-md shadow-teal-200 transition-all">
                        <Download className="w-4 h-4" />
                        Export CSV
                    </button>
                </div>
            </div>

            {emailError && (
                <div className="max-w-7xl mx-auto mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 text-sm flex items-center gap-2 print:hidden">
                    <AlertCircle className="w-4 h-4" /> {emailError}
                </div>
            )}

            <div id="printable-report" className="max-w-7xl mx-auto space-y-8">
                

                {/* Metrics Summary */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center gap-4">
                        <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center">
                            <FileText className="w-6 h-6 text-blue-600" />
                        </div>
                        <div>
                            <p className="text-sm font-bold text-gray-500 uppercase tracking-wide">Pages Scanned</p>
                            <h3 className="text-3xl font-bold text-gray-900">{summary?.total_pages || 0}</h3>
                        </div>
                    </div>
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center gap-4">
                        <div className="w-12 h-12 rounded-full bg-orange-50 flex items-center justify-center">
                            <AlertTriangle className="w-6 h-6 text-orange-600" />
                        </div>
                        <div>
                            <p className="text-sm font-bold text-gray-500 uppercase tracking-wide">Total Errors Found</p>
                            <h3 className="text-3xl font-bold text-gray-900">{summary?.total_errors || 0}</h3>
                        </div>
                    </div>
                    <div className={`p-6 rounded-2xl shadow-sm border flex items-center gap-4 ${summary?.status === 'Success' ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}`}>
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center ${summary?.status === 'Success' ? 'bg-green-100' : 'bg-red-100'}`}>
                            {summary?.status === 'Success' ? <CheckCircle className={`w-6 h-6 text-green-600`} /> : <AlertCircle className={`w-6 h-6 text-red-600`} />}
                        </div>
                        <div>
                            <p className={`text-sm font-bold uppercase tracking-wide ${summary?.status === 'Success' ? 'text-green-700' : 'text-red-700'}`}>Overall Status</p>
                            <h3 className={`text-2xl font-bold ${summary?.status === 'Success' ? 'text-green-800' : 'text-red-800'}`}>
                                {summary?.status === 'Success' ? 'Clean' : 'Needs Review'}
                            </h3>
                        </div>
                    </div>
                </div>

                {/* Pages Detail */}
                <div className="space-y-6">
                    <h2 className="text-2xl font-bold text-gray-900">Page Breakdown</h2>
                    
                    {pages && pages.length > 0 ? pages.map((page, idx) => (
                        <div key={idx} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                            <div className="px-6 py-5 border-b border-gray-100 bg-gray-50 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex items-center gap-3">
                                    {page.error_count === 0 ? (
                                        <CheckCircle className="w-6 h-6 text-green-500 shrink-0" />
                                    ) : (
                                        <AlertCircle className="w-6 h-6 text-orange-500 shrink-0" />
                                    )}
                                    <h3 className="text-lg font-bold text-gray-800 truncate max-w-2xl" title={page.url}>
                                        <a href={page.url} target="_blank" rel="noopener noreferrer" className="hover:text-teal-600 hover:underline transition-colors">
                                            {page.url} ↗
                                        </a>
                                    </h3>
                                </div>
                                <span className={`px-3 py-1 text-sm font-bold rounded-lg shrink-0 ${
                                    page.error_count === 0 
                                        ? 'bg-green-100 text-green-800' 
                                        : 'bg-orange-100 text-orange-800'
                                }`}>
                                    {page.error_count} {page.error_count === 1 ? 'Error' : 'Errors'} Found
                                </span>
                            </div>

                            <div className="p-6">
                                {page.error_count === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-6 text-center">
                                        <CheckCircle className="w-10 h-10 text-green-400 mb-3 opacity-50" />
                                        <p className="text-gray-500 font-medium">This page is clean. No textual errors were detected.</p>
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto">
                                        <table className="min-w-full divide-y divide-gray-200 border border-gray-100 rounded-xl hidden md:table">
                                            <thead className="bg-gray-50">
                                                <tr>
                                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-24">Type</th>
                                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-1/4">Original Text</th>
                                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-1/4">Suggested Correction</th>
                                                    <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Explanation</th>
                                                </tr>
                                            </thead>
                                            <tbody className="bg-white divide-y divide-gray-100">
                                                {page.errors && page.errors.map((err, eIdx) => (
                                                    <tr key={eIdx} className="hover:bg-gray-50 transition-colors">
                                                        <td className="px-5 py-4 whitespace-nowrap text-xs font-bold uppercase align-top">
                                                            <span className={`px-2 py-1 rounded inline-block ${
                                                                err.type === 'grammar' ? 'bg-purple-100 text-purple-700' :
                                                                err.type === 'spelling' ? 'bg-blue-100 text-blue-700' :
                                                                err.type === 'punctuation' ? 'bg-emerald-100 text-emerald-700' :
                                                                err.type === 'typo' ? 'bg-pink-100 text-pink-700' :
                                                                'bg-gray-100 text-gray-700'
                                                            }`}>
                                                                {err.type || 'error'}
                                                            </span>
                                                        </td>
                                                        <td className="px-5 py-4 text-sm text-gray-600 align-top line-through decoration-red-400 decoration-2">
                                                            {err.original_text}
                                                        </td>
                                                        <td className="px-5 py-4 text-sm font-semibold text-green-700 align-top bg-green-50">
                                                            {err.suggested_correction}
                                                        </td>
                                                        <td className="px-5 py-4 text-sm text-gray-600 align-top leading-relaxed italic">
                                                            {err.explanation}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>

                                        {/* Mobile view for errors */}
                                        <div className="md:hidden space-y-4">
                                            {page.errors && page.errors.map((err, eIdx) => (
                                                <div key={eIdx} className="border border-gray-100 rounded-xl p-4 bg-gray-50">
                                                    <div className="flex justify-between items-center mb-3">
                                                        <span className="text-xs font-bold uppercase bg-gray-200 text-gray-700 px-2 py-1 rounded">
                                                            {err.type || 'error'}
                                                        </span>
                                                    </div>
                                                    <div className="space-y-3">
                                                        <div>
                                                            <p className="text-xs font-bold text-gray-400 uppercase">Original</p>
                                                            <p className="text-sm line-through text-red-500">{err.original_text}</p>
                                                        </div>
                                                        <div>
                                                            <p className="text-xs font-bold text-gray-400 uppercase">Suggested</p>
                                                            <p className="text-sm font-bold text-green-600">{err.suggested_correction}</p>
                                                        </div>
                                                        <div>
                                                            <p className="text-xs font-bold text-gray-400 uppercase">Explanation</p>
                                                            <p className="text-sm text-gray-600 italic">{err.explanation}</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )) : (
                        <div className="text-center py-12 bg-white rounded-xl border border-gray-100">
                            <p className="text-gray-500">No pages were analyzed.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ContentReviewDashboard;
