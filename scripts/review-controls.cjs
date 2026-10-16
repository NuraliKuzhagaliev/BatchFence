// Test operator input, not independent human validation.
module.exports = async function reviewControls(page, choice) {
  await page.getByLabel('Accepted affected lots · comma separated', {exact:true}).fill(choice.affected.join(', '));
  await page.getByLabel('Unresolved lots · comma separated', {exact:true}).fill((choice.uncertain || []).join(', '));
  await page.getByLabel('Explicitly excluded lots · comma separated', {exact:true}).fill((choice.excluded || []).join(', '));
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
