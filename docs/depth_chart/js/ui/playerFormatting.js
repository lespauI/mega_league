export function formatName(player) {
  if (!player) return '';
  const first = player.firstName || '';
  const last = player.lastName || '';
  const initial = first.charAt(0);
  return initial ? `${initial}.${last}` : last;
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

