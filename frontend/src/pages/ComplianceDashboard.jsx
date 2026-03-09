import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Printer, Download, AlertTriangle, CheckCircle, XCircle, X } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

const ComplianceDashboard = () => {
    const [report, setReport] = useState(null);
    const [checklistData, setChecklistData] = useState(null);
    const [isChecklistOpen, setIsChecklistOpen] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        const storedReport = localStorage.getItem('latest_compliance_report');
        if (storedReport) {
            try {
                setReport(JSON.parse(storedReport));
            } catch (e) {
                console.error("Failed to parse report", e);
            }
        }
    }, []);

    const openChecklist = (checklist, ticketKey) => {
        setChecklistData({ 
            title: `Compliance Checklist - ${ticketKey}`, 
            items: checklist || [] 
        });
        setIsChecklistOpen(true);
    };

    const closeChecklist = () => {
        setIsChecklistOpen(false);
        setChecklistData(null);
    };

    if (!report) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <h2 className="text-2xl font-bold text-gray-700 mb-2">No Report Found</h2>
                    <p className="text-gray-500 mb-4">Please run the Compliance Agent first to generate a report.</p>
                    <button 
                        onClick={() => navigate('/agent/compliance-bot')}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                        Go to Agent
                    </button>
                </div>
            </div>
        );
    }

    const getStatusColor = (status) => {
        if (['Done', 'Completed', 'Closed'].includes(status)) return 'bg-green-100 text-green-800';
        if (['In Progress', 'In Review'].includes(status)) return 'bg-blue-100 text-blue-800';
        return 'bg-gray-100 text-gray-800';
    };

    const getAlignmentColor = (status) => {
        if (status === 'Aligned') return 'bg-green-100 text-green-800';
        if (status === 'Misaligned') return 'bg-red-100 text-red-800';
        return 'bg-yellow-100 text-yellow-800';
    };

    const downloadCSV = () => {
        if (!report) return;
        const headers = ['Ticket', 'Summary', 'Status', 'Severity', 'Alignment', 'Completion %', 'Gaps', 'Actions'];
        const csvRows = [headers.join(',')];
        report.forEach(row => {
            const gaps = row.compliance_gaps ? row.compliance_gaps.join('; ') : '';
            const actions = row.recommended_actions ? row.recommended_actions.join('; ') : '';
            const values = [
                row.key,
                `"${(row.summary || '').replace(/"/g, '""')}"`,
                row.status,
                row.priority || 'N/A',
                row.alignment_status,
                row.completion_percentage,
                `"${gaps.replace(/"/g, '""')}"`,
                `"${actions.replace(/"/g, '""')}"`
            ];
            csvRows.push(values.join(','));
        });
        const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `compliance_report_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans">
            {/* Header */}
            <div className="max-w-7xl mx-auto mb-8 flex justify-between items-center print:hidden">
                <style>{`
                    @media print {
                        body * { visibility: hidden; }
                        #printable-report, #printable-report * { visibility: visible; }
                        #printable-report { position: absolute; left: 0; top: 0; width: 100%; margin: 0; padding: 0; border: none; }
                        @page { margin: 1cm; size: landscape; }
                        .no-print { display: none !important; }
                    }
                `}</style>
                <div className="flex items-center gap-4">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Compliance Audit Report</h1>
                        <p className="text-gray-500">Project Level Analysis • {new Date().toLocaleDateString()}</p>
                    </div>
                </div>
                <div className="flex gap-3">
                    <button 
                        onClick={() => window.print()}
                        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 shadow-sm"
                    >
                        <Printer className="w-4 h-4" />
                        Print / PDF
                    </button>
                    <button onClick={downloadCSV} className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 shadow-sm">
                        <Download className="w-4 h-4" />
                        Export CSV
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div id="printable-report" className="max-w-[1600px] mx-auto space-y-12">
                
                {/* Section 1: Satisfied Tickets */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden print:shadow-none print:border-0">
                    <div className="px-6 py-4 border-b border-gray-200 bg-green-50">
                        <h2 className="text-xl font-bold text-green-800 flex items-center gap-2">
                            <CheckCircle className="w-5 h-5" />
                            1. Satisfied Tickets
                        </h2>
                        <p className="text-green-600 text-sm mt-1">Tickets that passed all strict compliance criteria.</p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Ticket</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-1/2">Summary</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Severity</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Assignee</th>
                                    <th scope="col" className="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Checklist</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {report.filter(r => r.is_satisfied === true).length > 0 ? (
                                    report.filter(r => r.is_satisfied === true).map((row, idx) => (
                                        <tr key={idx} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600 align-top">{row.key}</td>
                                            <td className="px-6 py-4 text-sm text-gray-800 align-top font-medium">{row.summary}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-xs align-top">
                                                <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(row.status)}`}>{row.status}</span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 align-top">{row.priority || 'N/A'}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 align-top">{row.assignee || 'Unassigned'}</td>
                                            <td className="px-6 py-4 text-center align-top no-print">
                                                <button 
                                                    onClick={() => openChecklist(row.compliance_checklist, row.key)}
                                                    className="text-blue-600 hover:text-blue-800 text-xs font-bold hover:underline focus:outline-none uppercase tracking-wide"
                                                >
                                                    View Checklist
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan="6" className="px-6 py-8 text-center text-gray-500 italic">No fully satisfied tickets found.</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Section 2: Dissatisfied Tickets */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden print:shadow-none print:border-0">
                    <div className="px-6 py-4 border-b border-gray-200 bg-red-50">
                        <h2 className="text-xl font-bold text-red-800 flex items-center gap-2">
                            <XCircle className="w-5 h-5" />
                            2. Dissatisfied Tickets
                        </h2>
                        <p className="text-red-600 text-sm mt-1">Tickets failing one or more compliance checks.</p>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-24">Ticket</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-1/4">Summary</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-32">Status</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-32">Severity</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-32">Alignment</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider w-32">Comp. %</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Deficiencies & Gaps</th>
                                    <th scope="col" className="px-6 py-3 text-center text-xs font-bold text-gray-500 uppercase tracking-wider">Checklist</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {report.filter(r => !r.is_satisfied).length > 0 ? (
                                    report.filter(r => !r.is_satisfied).map((row, idx) => (
                                        <tr key={idx} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600 align-top">
                                                {row.key}
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-800 align-top leading-relaxed font-medium">
                                                {row.summary}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-xs align-top">
                                                <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(row.status)}`}>
                                                    {row.status}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 align-top">
                                                {row.priority || 'N/A'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm align-top">
                                                <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getAlignmentColor(row.alignment_status)}`}>
                                                    {row.alignment_status}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 align-top">
                                                <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                                                    <div 
                                                        className="h-2 rounded-full bg-red-500" 
                                                        style={{ width: `${row.completion_percentage}%` }}
                                                    ></div>
                                                </div>
                                                <span className="text-xs font-mono">{row.completion_percentage}%</span>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-600 align-top space-y-2">
                                                {/* Gaps List */}
                                                {(row.compliance_gaps && row.compliance_gaps.length > 0) ? (
                                                    <div className="mb-2">
                                                        <p className="text-xs font-bold text-red-600 uppercase mb-1">Missing / Incomplete Fields:</p>
                                                        <ul className="list-disc list-inside text-xs text-red-700 font-medium">
                                                            {row.compliance_gaps.map((gap, i) => <li key={i}>{gap}</li>)}
                                                        </ul>
                                                    </div>
                                                ) : (
                                                    <p className="text-xs text-red-500 italic">Unspecified compliance failure.</p>
                                                )}

                                                {/* Irrelevant Attachments */}
                                                {row.attachment_check?.irrelevant_files?.length > 0 && (
                                                    <div className="mt-2">
                                                        <p className="text-xs font-bold text-orange-600 uppercase mb-1 flex items-center gap-1">
                                                            📎 Irrelevant Attachments:
                                                        </p>
                                                        <ul className="space-y-1">
                                                            {row.attachment_check.irrelevant_files.map((file, i) => (
                                                                <li key={i} className="flex items-center gap-2 text-xs">
                                                                    <span className="text-orange-700 font-medium truncate max-w-[160px]" title={file.filename}>
                                                                        {file.filename}
                                                                    </span>
                                                                    <span className="inline-flex items-center px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-mono font-semibold text-[10px] shrink-0">
                                                                        score: {typeof file.score === 'number' ? file.score.toFixed(2) : file.score}
                                                                    </span>
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}

                                                {/* Actions */}
                                                {row.recommended_actions && row.recommended_actions.length > 0 && (
                                                    <div>
                                                        <p className="text-xs font-bold text-blue-600 uppercase mb-1">Recommended Actions:</p>
                                                        <ul className="list-disc list-inside text-xs text-gray-700">
                                                            {row.recommended_actions.map((action, i) => <li key={i}>{action}</li>)}
                                                        </ul>
                                                    </div>
                                                )}
                                            </td>
                                            <td className="px-6 py-4 text-center align-top no-print">
                                                <button 
                                                    onClick={() => openChecklist(row.compliance_checklist, row.key)}
                                                    className="text-blue-600 hover:text-blue-800 text-xs font-bold hover:underline focus:outline-none uppercase tracking-wide"
                                                >
                                                    View Checklist
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan="7" className="px-6 py-8 text-center text-gray-500 italic">No dissatisfied tickets found. Great job!</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Checklist Modal - Only shows when requested */}
            <AnimatePresence>
                {isChecklistOpen && checklistData && (
                    <div className="fixed inset-0 z-50 flex items-start justify-end bg-black/50 backdrop-blur-sm print:hidden" onClick={closeChecklist}>
                        <motion.div 
                            initial={{ x: "100%" }}
                            animate={{ x: 0 }}
                            exit={{ x: "100%" }}
                            transition={{ type: "spring", stiffness: 300, damping: 30 }}
                            onClick={(e) => e.stopPropagation()}
                            className="bg-white shadow-2xl h-full w-full max-w-2xl flex flex-col overflow-hidden"
                        >
                            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50">
                                <h2 className="text-xl font-bold text-gray-900">{checklistData.title}</h2>
                                <button onClick={closeChecklist} className="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-200 transition-colors">
                                    <X size={20} />
                                </button>
                            </div>
                            
                            <div className="flex-1 overflow-y-auto p-6">
                                {checklistData.items && checklistData.items.length > 0 ? (
                                    <table className="w-full text-sm text-left border-collapse rounded-lg overflow-hidden border border-gray-200">
                                        <thead className="bg-gray-100 text-gray-600 uppercase text-xs font-semibold sticky top-0">
                                            <tr>
                                                <th className="px-4 py-3 border-b border-gray-200 w-1/4">Category</th>
                                                <th className="px-4 py-3 border-b border-gray-200 w-1/3">Specific Check</th>
                                                <th className="px-4 py-3 border-b border-gray-200 w-24 text-center">Result</th>
                                                <th className="px-4 py-3 border-b border-gray-200">Comment</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-100">
                                            {checklistData.items.map((item, idx) => (
                                                <tr key={idx} className="hover:bg-gray-50">
                                                    <td className="px-4 py-3 font-medium text-gray-800 align-top">{item.category}</td>
                                                    <td className="px-4 py-3 text-gray-600 align-top">{item.check}</td>
                                                    <td className="px-4 py-3 text-center align-top">
                                                        <span className={`inline-flex px-2 py-1 rounded-md text-xs font-bold ${
                                                            item.status === 'Pass' ? 'bg-green-100 text-green-700' :
                                                            item.status === 'Fail' ? 'bg-red-100 text-red-700' :
                                                            'bg-gray-100 text-gray-600'
                                                        }`}>
                                                            {item.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-gray-600 italic align-top">
                                                        {item.comment || '-'}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                ) : (
                                    <div className="text-center py-12 text-gray-400">
                                        <div className="mb-2 font-medium">No checklist data found</div>
                                        <div className="text-xs">Processing may have failed or no checks were applicable.</div>
                                    </div>
                                )}
                            </div>
                            
                            <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end">
                                <button 
                                    onClick={closeChecklist}
                                    className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 shadow-sm transition-all"
                                >
                                    Close Drawer
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default ComplianceDashboard;
