// Test operator input, not independent human validation.
module.exports = async function reviewControls(page, choice) {
  for (const id of choice.affected) await page.getByLabel('Disposition of '+id,{exact:true}).selectOption('affected');
  for (const id of choice.uncertain || []) await page.getByLabel('Disposition of '+id,{exact:true}).selectOption('unresolved');
  for (const id of choice.excluded || []) await page.getByLabel('Disposition of '+id,{exact:true}).selectOption('excluded');
  await page.getByLabel('Incident scope certainty', {exact:true}).selectOption(choice.resolved ? 'resolved' : 'unresolved');
  if (choice.resolved) {
    await page.getByLabel('Scope resolution basis · exact source quote', {exact:true}).fill(choice.quote);
    await page.getByLabel('I reviewed inventory, lineage and the bounded completeness manifest. Uncheck to decline narrowing.').check();
  }
  await page.getByLabel('Review explanation · scope and exclusions', {exact:true}).fill(choice.note);
  await page.getByLabel('I checked lot IDs, exclusions, qualifiers and whether this notice supersedes prior scope.').check();
};
module.exports.fixture = async function fixtureReview(page, affected) {
  return module.exports(page, {affected, resolved:true, quote:'Affected lots: ' + affected.join(', '),
    note:'Automated synthetic test review: the fixture notice defines the complete supplier scope.'});
};
