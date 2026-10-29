/**
 * Shared demonstration dataset for the Blood Bank & Donor Management System frontend prototype.
 * All data here is FICTIONAL and exists only so every page shows consistent sample values.
 * None of it represents real people, real inventory, or real requests.
 */

const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

const MOCK_DONORS = [
  { id: 1, name: "Aarav Sharma", bloodGroup: "O+", city: "Pune", phone: "98XXX XX101", email: "aarav.sharma@example.com", lastDonation: "2026-07-12" },
  { id: 2, name: "Priya Nair", bloodGroup: "A+", city: "Mumbai", phone: "98XXX XX102", email: "priya.nair@example.com", lastDonation: "2026-05-02" },
  { id: 3, name: "Rohan Mehta", bloodGroup: "B+", city: "Pune", phone: "98XXX XX103", email: "rohan.mehta@example.com", lastDonation: "2026-08-20" },
  { id: 4, name: "Sneha Iyer", bloodGroup: "AB+", city: "Bengaluru", phone: "98XXX XX104", email: "sneha.iyer@example.com", lastDonation: "2026-03-15" },
  { id: 5, name: "Kabir Khan", bloodGroup: "O-", city: "Delhi", phone: "98XXX XX105", email: "kabir.khan@example.com", lastDonation: "2026-09-01" },
  { id: 6, name: "Ishita Verma", bloodGroup: "A-", city: "Pune", phone: "98XXX XX106", email: "ishita.verma@example.com", lastDonation: "2026-06-18" },
  { id: 7, name: "Dev Patel", bloodGroup: "B-", city: "Ahmedabad", phone: "98XXX XX107", email: "dev.patel@example.com", lastDonation: "2026-01-29" },
  { id: 8, name: "Ananya Reddy", bloodGroup: "AB-", city: "Hyderabad", phone: "98XXX XX108", email: "ananya.reddy@example.com", lastDonation: "2026-04-22" },
  { id: 9, name: "Vivaan Joshi", bloodGroup: "O+", city: "Mumbai", phone: "98XXX XX109", email: "vivaan.joshi@example.com", lastDonation: "2026-08-05" },
  { id: 10, name: "Meera Pillai", bloodGroup: "A+", city: "Bengaluru", phone: "98XXX XX110", email: "meera.pillai@example.com", lastDonation: "2026-02-11" },
  { id: 11, name: "Arjun Rao", bloodGroup: "B+", city: "Delhi", phone: "98XXX XX111", email: "arjun.rao@example.com", lastDonation: "2026-07-30" },
  { id: 12, name: "Kavya Menon", bloodGroup: "O-", city: "Pune", phone: "98XXX XX112", email: "kavya.menon@example.com", lastDonation: "2026-05-27" },
];

const MOCK_INVENTORY = [
  { bloodGroup: "A+", units: 42, capacity: 60, expiring: 3 },
  { bloodGroup: "A-", units: 9, capacity: 40, expiring: 1 },
  { bloodGroup: "B+", units: 35, capacity: 60, expiring: 0 },
  { bloodGroup: "B-", units: 6, capacity: 40, expiring: 2 },
  { bloodGroup: "AB+", units: 18, capacity: 30, expiring: 0 },
  { bloodGroup: "AB-", units: 4, capacity: 20, expiring: 1 },
  { bloodGroup: "O+", units: 51, capacity: 70, expiring: 4 },
  { bloodGroup: "O-", units: 7, capacity: 40, expiring: 0 },
];

const MOCK_REQUESTS = [
  { id: "REQ-1001", requester: "City Care Hospital", bloodGroup: "O-", units: 4, city: "Pune", urgency: "Critical", status: "Pending", date: "2026-10-26" },
  { id: "REQ-1002", requester: "Riya Deshmukh", bloodGroup: "A+", units: 2, city: "Mumbai", urgency: "High", status: "Approved", date: "2026-10-24" },
  { id: "REQ-1003", requester: "Sunrise Medical Center", bloodGroup: "B+", units: 6, city: "Delhi", urgency: "Medium", status: "Fulfilled", date: "2026-10-20" },
  { id: "REQ-1004", requester: "Aditya Kulkarni", bloodGroup: "AB-", units: 1, city: "Hyderabad", urgency: "High", status: "Rejected", date: "2026-10-18" },
  { id: "REQ-1005", requester: "Hopewell Clinic", bloodGroup: "O+", units: 3, city: "Bengaluru", urgency: "Medium", status: "Pending", date: "2026-10-27" },
  { id: "REQ-1006", requester: "Nisha Agarwal", bloodGroup: "A-", units: 2, city: "Pune", urgency: "Critical", status: "Approved", date: "2026-10-25" },
];

const MOCK_STATS = {
  registeredDonors: 1284,
  availableUnits: MOCK_INVENTORY.reduce((sum, i) => sum + i.units, 0),
  activeRequests: MOCK_REQUESTS.filter((r) => r.status === "Pending").length,
  partnerBanks: 17,
};

function getStockStatus(units, capacity) {
  const ratio = units / capacity;
  if (ratio <= 0.15) return { label: "Critical", variant: "danger" };
  if (ratio <= 0.35) return { label: "Low", variant: "warning" };
  return { label: "Available", variant: "success" };
}

function getUrgencyVariant(urgency) {
  switch (urgency) {
    case "Critical": return "danger";
    case "High": return "warning";
    case "Medium": return "info";
    default: return "secondary";
  }
}

function getStatusVariant(status) {
  switch (status) {
    case "Pending": return "secondary";
    case "Approved": return "info";
    case "Fulfilled": return "success";
    case "Rejected": return "danger";
    default: return "secondary";
  }
}
