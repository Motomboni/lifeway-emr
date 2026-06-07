/**
 * Organizations Management Page
 *
 * Admin-only: create organizations, view members, add members.
 * Part of SaaS multi-tenancy.
 */
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useRolePermissions } from '../hooks/useRolePermissions';
import {
  getOrganizationMemberships,
  createOrganization,
  getOrganizationMembers,
  addOrganizationMember,
  addOrganizationMemberByEmail,
  type Organization,
  type OrganizationMember,
} from '../api/organizations';
import { useToast } from '../hooks/useToast';
import ToastContainer from '../components/common/ToastContainer';
import styles from '../styles/Organizations.module.css';

export default function OrganizationsPage() {
  const { user } = useAuth();
  const { isAdmin } = useRolePermissions();
  const { toasts, showSuccess, showError, removeToast } = useToast();
  const [memberships, setMemberships] = useState<{ organization: Organization }[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createData, setCreateData] = useState({ name: '', slug: '', email: '' });
  const [creating, setCreating] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [addUserId, setAddUserId] = useState('');
  const [addEmail, setAddEmail] = useState('');
  const [addingMember, setAddingMember] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const list = await getOrganizationMemberships();
        setMemberships(list.map((m: { organization: Organization }) => ({ organization: m.organization })));
      } catch (err: any) {
        showError(err.message || 'Failed to load organizations');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [showError]);

  useEffect(() => {
    if (!selectedOrg) {
      setMembers([]);
      return;
    }
    const load = async () => {
      try {
        const list = await getOrganizationMembers(selectedOrg.id);
        setMembers(list);
      } catch (err: any) {
        showError(err.message || 'Failed to load members');
      }
    };
    load();
  }, [selectedOrg, showError]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createData.name.trim() || !createData.slug.trim()) {
      showError('Name and slug are required');
      return;
    }
    setCreating(true);
    try {
      await createOrganization({
        name: createData.name.trim(),
        slug: createData.slug.trim().toLowerCase().replace(/\s+/g, '-'),
        email: createData.email.trim() || undefined,
      });
      showSuccess('Organization created');
      setShowCreateForm(false);
      setCreateData({ name: '', slug: '', email: '' });
      const list = await getOrganizationMemberships();
      setMemberships(list.map((m: { organization: Organization }) => ({ organization: m.organization })));
    } catch (err: any) {
      showError(err.responseData?.detail || err.message || 'Failed to create organization');
    } finally {
      setCreating(false);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrg) return;
    if (!addEmail.trim() && !addUserId.trim()) {
      showError('Enter staff email or user ID');
      return;
    }
    setAddingMember(true);
    try {
      if (addEmail.trim()) {
        await addOrganizationMemberByEmail(selectedOrg.id, addEmail.trim());
      } else {
        const uid = parseInt(addUserId, 10);
        if (isNaN(uid)) {
          showError('Invalid user ID');
          setAddingMember(false);
          return;
        }
        await addOrganizationMember(selectedOrg.id, uid);
      }
      showSuccess('Member added — invitation email sent if address was provided');
      setAddUserId('');
      setAddEmail('');
      const list = await getOrganizationMembers(selectedOrg.id);
      setMembers(list);
    } catch (err: any) {
      showError(err.responseData?.detail || err.message || 'Failed to add member');
    } finally {
      setAddingMember(false);
    }
  };

  if (!isAdmin) {
    return (
      <div className={styles.page}>
        <h1>Organizations</h1>
        <p>Access denied. Admin only.</p>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerTitle}>
          <Link to="/dashboard" className={styles.backLink}>
            &larr; Back to Dashboard
          </Link>
          <h1>Organizations</h1>
        </div>
        <button
          type="button"
          className={styles.createButton}
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? 'Cancel' : '+ Create Organization'}
        </button>
      </div>

      {showCreateForm && (
        <form onSubmit={handleCreate} className={styles.form}>
          <h3>Create Organization</h3>
          <p className={styles.hint}>
            For a new clinic account with owner login, use{' '}
            <Link to="/register">Register → Create clinic</Link> instead.
            This form adds another organization to your existing admin account.
          </p>
          <label>Name *</label>
          <input
            type="text"
            value={createData.name}
            onChange={(e) => setCreateData({ ...createData, name: e.target.value })}
            placeholder="Clinic Name"
            required
          />
          <label>Slug *</label>
          <input
            type="text"
            value={createData.slug}
            onChange={(e) => setCreateData({ ...createData, slug: e.target.value })}
            placeholder="clinic-slug"
            required
          />
          <label>Email</label>
          <input
            type="email"
            value={createData.email}
            onChange={(e) => setCreateData({ ...createData, email: e.target.value })}
            placeholder="contact@clinic.com"
          />
          <button type="submit" disabled={creating}>
            {creating ? 'Creating...' : 'Create'}
          </button>
        </form>
      )}

      <div className={styles.content}>
        <div className={styles.orgList}>
          <h3>Your Organizations</h3>
          {loading ? (
            <p>Loading...</p>
          ) : (
            <ul>
              {memberships.map((m) => (
                <li
                  key={m.organization.id}
                  className={selectedOrg?.id === m.organization.id ? styles.selected : ''}
                >
                  <button
                    type="button"
                    onClick={() => setSelectedOrg(m.organization)}
                  >
                    {m.organization.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {selectedOrg && (
          <div className={styles.membersPanel}>
            <h3>Members: {selectedOrg.name}</h3>
            <ul className={styles.memberList}>
              {members.map((m) => (
                <li key={m.id}>
                  {m.first_name} {m.last_name} ({m.username}) – {m.role}
                </li>
              ))}
            </ul>
            <form onSubmit={handleAddMember} className={styles.addMemberForm}>
              <input
                type="email"
                placeholder="Staff email (after they registered)"
                value={addEmail}
                onChange={(e) => setAddEmail(e.target.value)}
              />
              <input
                type="number"
                placeholder="Or user ID"
                value={addUserId}
                onChange={(e) => setAddUserId(e.target.value)}
              />
              <button type="submit" disabled={addingMember}>
                {addingMember ? 'Adding...' : 'Add Member'}
              </button>
            </form>
          </div>
        )}
      </div>
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
