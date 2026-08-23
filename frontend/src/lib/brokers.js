export const BROKERS = [
  { code: 'UNASSIGNED', name: 'Unassigned / Chưa gán' },
  { code: 'TCBS', name: 'TCBS' },
  { code: 'SSI', name: 'SSI' },
  { code: 'DNSE', name: 'DNSE' },
  { code: 'VPS', name: 'VPS' },
  { code: 'VCBS', name: 'VCBS' },
  { code: 'HSC', name: 'HSC' },
  { code: 'VNDIRECT', name: 'VNDIRECT' },
  { code: 'OTHER', name: 'Other / Khác' },
];

export const BROKER_CODES = new Set(BROKERS.map((item) => item.code));
