/**
 * Bill Item Table Component
 * 
 * Displays bill items in a table format, optionally grouped by department.
 * Per EMR Rules: Read-only, no edit/delete buttons.
 */
import React, { useMemo } from 'react';
import { formatCurrency } from '../../utils/currency';

export interface BillItem {
  id: number;
  bill_id?: number;
  department: 'CONSULTATION' | 'LAB' | 'RADIOLOGY' | 'PHARMACY' | 'PROCEDURE' | 'MISC';
  service_name: string;
  amount: string | number;
  status: 'UNPAID' | 'PAID' | 'INSURANCE';
  created_at?: string;
  created_by?: number;
}

interface BillItemTableProps {
  billItems: BillItem[];
  groupedByDepartment?: boolean;
}

const DEPARTMENT_LABELS: Record<string, string> = {
  CONSULTATION: 'Consultation',
  LAB: 'Laboratory',
  RADIOLOGY: 'Radiology',
  PHARMACY: 'Pharmacy',
  PROCEDURE: 'Procedures',
  MISC: 'Miscellaneous',
};

const DEPARTMENT_ICONS: Record<string, string> = {
  CONSULTATION: '🩺',
  LAB: '🧪',
  RADIOLOGY: '📷',
  PHARMACY: '💊',
  PROCEDURE: '⚕️',
  MISC: '📋',
};

export default function BillItemTable({
  billItems,
  groupedByDepartment = true,
}: BillItemTableProps) {
  // Group items by department if requested
  const groupedItems = useMemo(() => {
    if (!groupedByDepartment) {
      return { 'ALL': billItems };
    }

    return billItems.reduce((acc, item) => {
      const dept = item.department;
      if (!acc[dept]) {
        acc[dept] = [];
      }
      acc[dept].push(item);
      return acc;
    }, {} as Record<string, BillItem[]>);
  }, [billItems, groupedByDepartment]);

  // Calculate totals
  const totalAmount = useMemo(() => {
    return billItems.reduce((sum, item) => {
      const amount = typeof item.amount === 'string' ? parseFloat(item.amount) : item.amount;
      return sum + (isNaN(amount) ? 0 : amount);
    }, 0);
  }, [billItems]);

  // Get status badge styling
  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'PAID':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'INSURANCE':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'UNPAID':
      default:
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    }
  };

  // Get status label
  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'PAID':
        return 'Paid';
      case 'INSURANCE':
        return 'Insurance';
      case 'UNPAID':
      default:
        return 'Unpaid';
    }
  };

  if (billItems.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-8 text-center border border-gray-200">
        <p className="text-gray-500">No bill items found</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Service
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Amount
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {Object.entries(groupedItems).map(([department, items]) => {
              const departmentTotal = items.reduce((sum, item) => {
                const amount = typeof item.amount === 'string' ? parseFloat(item.amount) : item.amount;
                return sum + (isNaN(amount) ? 0 : amount);
              }, 0);

              return (
                <React.Fragment key={department}>
                  {/* Department Header Row */}
                  {groupedByDepartment && department !== 'ALL' && (
                    <tr className="bg-gray-100 border-t-2 border-gray-300">
                      <td colSpan={3} className="px-4 py-3">
                        <div className="flex items-center space-x-2">
                          <span className="text-lg">
                            {DEPARTMENT_ICONS[department] || '📋'}
                          </span>
                          <span className="font-semibold text-gray-900">
                            {DEPARTMENT_LABELS[department] || department}
                          </span>
                          <span className="text-sm text-gray-500">
                            ({items.length} {items.length === 1 ? 'item' : 'items'})
                          </span>
                          <span className="ml-auto font-semibold text-gray-700">
                            Subtotal: {formatCurrency(departmentTotal.toString())}
                          </span>
                        </div>
                      </td>
                    </tr>
                  )}

                  {/* Bill Items */}
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="font-medium text-gray-900">
                            {item.service_name}
                          </span>
                          {item.created_at && (
                            <span className="text-xs text-gray-500 mt-1">
                              {new Date(item.created_at).toLocaleDateString('en-NG', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                              })}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-semibold text-gray-900">
                          {formatCurrency(item.amount)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`
                            inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border
                            ${getStatusBadgeClass(item.status)}
                          `}
                        >
                          {getStatusLabel(item.status)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </React.Fragment>
              );
            })}
          </tbody>
          <tfoot className="bg-gray-50 border-t-2 border-gray-300">
            <tr>
              <td colSpan={2} className="px-4 py-4 text-right">
                <span className="text-sm font-semibold text-gray-700 uppercase">
                  Total Amount:
                </span>
              </td>
              <td className="px-4 py-4 text-right">
                <span className="text-lg font-bold text-gray-900">
                  {formatCurrency(totalAmount.toString())}
                </span>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Status Legend */}
      <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
        <div className="flex items-center space-x-4 text-xs text-gray-600">
          <span className="font-medium">Status:</span>
          <div className="flex items-center space-x-1">
            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800 border border-yellow-200">
              Unpaid
            </span>
            <span className="text-gray-400">•</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200">
              Insurance
            </span>
            <span className="text-gray-400">•</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-green-100 text-green-800 border border-green-200">
              Paid
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

