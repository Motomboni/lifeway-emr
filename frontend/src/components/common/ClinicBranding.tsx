/**

 * Clinic header branding — Lifeway uses the static LMC logo (single-clinic deploy).

 */

import React from 'react';

import Logo from './Logo';



interface ClinicBrandingProps {

  size?: 'small' | 'medium' | 'large';

  showText?: boolean;

}



export default function ClinicBranding({

  size = 'medium',

  showText = false,

}: ClinicBrandingProps) {

  return <Logo size={size} showText={showText} />;

}


