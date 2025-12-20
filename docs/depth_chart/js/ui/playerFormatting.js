export function formatName(player) {
  if (!player) return '';
  const first = player.firstName || '';
  const last = player.lastName || '';
  const initial = first.charAt(0);
  return initial ? `${initial}.${last}` : last;
}

export function formatSalary(player) {
  if (!player) return '';
  const capHit = player.capHit;
  if (capHit === undefined || capHit === null || !Number.isFinite(capHit)) return '';
  const millions = capHit / 1_000_000;
  if (millions >= 1) {
    return `${millions.toFixed(1)}m`;
  }
  const thousands = capHit / 1_000;
  return `${thousands.toFixed(0)}k`;
}

export function getDevTraitInfo(player) {
  if (!player) return { label: '', colorClass: '' };
  const trait = String(player.devTrait || '').toLowerCase().trim();
  if (trait === '3' || trait === 'xfactor' || trait === 'x-factor' || trait === 'x') {
    return { label: 'X', colorClass: 'dev-trait--x' };
  }
  if (trait === '2' || trait === 'superstar' || trait === 'ss') {
    return { label: 'SS', colorClass: 'dev-trait--ss' };
  }
  if (trait === '1' || trait === 'star' || trait === 's') {
    return { label: '★', colorClass: 'dev-trait--star' };
  }
  return { label: '', colorClass: '' };
}

export function getContractSummary(player) {
  if (!player) {
    return { label: '', isFaAfterSeason: false };
  }

  const lengthRaw =
    player.contractLength !== undefined && player.contractLength !== null
      ? Number(player.contractLength)
      : undefined;
  const yearsLeftRaw =
    player.contractYearsLeft !== undefined && player.contractYearsLeft !== null
      ? Number(player.contractYearsLeft)
      : undefined;

  const length = Number.isFinite(lengthRaw) ? lengthRaw : yearsLeftRaw ?? null;
  const yearsLeft = Number.isFinite(yearsLeftRaw) ? yearsLeftRaw : null;

  const isFaNow = !!player.isFreeAgent;
  const isFaAfterSeason = !isFaNow && yearsLeft !== null && Number(yearsLeft) === 1;

  let label = '';
  if (isFaNow) {
    label = 'FA';
  } else if (length !== null && yearsLeft !== null) {
    label = `${length} yrs (${yearsLeft} left)`;
  } else if (yearsLeft !== null) {
    const yrs = yearsLeft;
    label = `${yrs} yr${yrs === 1 ? '' : 's'} left`;
  }

  return { label, isFaAfterSeason };
}

