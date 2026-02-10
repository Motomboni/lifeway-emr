/**
 * Type declarations for react-icons to fix TypeScript compatibility issues
 */
declare module 'react-icons/fa' {
  import { FC, SVGProps } from 'react';
  
  interface IconProps extends SVGProps<SVGSVGElement> {
    size?: string | number;
  }
  
  export const FaLock: FC<IconProps>;
  export const FaUnlock: FC<IconProps>;
  export const FaCalendarPlus: FC<IconProps>;
  export const FaUserMd: FC<IconProps>;
  export const FaTimesCircle: FC<IconProps>;
  export const FaFileMedical: FC<IconProps>;
  export const FaFlask: FC<IconProps>;
  export const FaVial: FC<IconProps>;
  export const FaXRay: FC<IconProps>;
  export const FaPills: FC<IconProps>;
  export const FaMoneyBillWave: FC<IconProps>;
  export const FaProcedures: FC<IconProps>;
  export const FaBed: FC<IconProps>;
  export const FaHeartbeat: FC<IconProps>;
  export const FaNotesMedical: FC<IconProps>;
  export const FaSyringe: FC<IconProps>;
  export const FaMicroscope: FC<IconProps>;
  export const FaFileUpload: FC<IconProps>;
  export const FaShareSquare: FC<IconProps>;
  export const FaFileAlt: FC<IconProps>;
  export const FaChevronUp: FC<IconProps>;
  export const FaChevronDown: FC<IconProps>;
  export const FaExternalLinkAlt: FC<IconProps>;
  export const FaSync: FC<IconProps>;
  export const FaCalendarCheck: FC<IconProps>;
  export const FaPrint: FC<IconProps>;
  export const FaCheckCircle: FC<IconProps>;
  export const FaCashRegister: FC<IconProps>;
  export const FaCreditCard: FC<IconProps>;
  export const FaWallet: FC<IconProps>;
  export const FaHospital: FC<IconProps>;
  export const FaExclamationTriangle: FC<IconProps>;
  export const FaClock: FC<IconProps>;
  export const FaSpinner: FC<IconProps>;
  export const FaFileImage: FC<IconProps>;
  export const FaCloudUploadAlt: FC<IconProps>;
  export const FaRedo: FC<IconProps>;
  export const FaWifi: FC<IconProps>;
  export const FaFilter: FC<IconProps>;
  export const FaEye: FC<IconProps>;
  export const FaDollarSign: FC<IconProps>;
  export const FaUsers: FC<IconProps>;
  export const FaChartPie: FC<IconProps>;
  export const FaChartLine: FC<IconProps>;
  export const FaChartBar: FC<IconProps>;
}

