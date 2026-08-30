/**
 * Standalone cap-limit-breach checker for Alleyn CC — Google Apps Script port
 * of cap_limits.py.
 *
 * Finds players who have played enough games for higher teams (1s, 2s, 3s...)
 * that they are no longer eligible ("cup-tied") to play for a lower team, and
 * builds a message grouped by the lowest team each capped player can still
 * play for.
 *
 * Setup: in the Apps Script editor, go to Project Settings > Script
 * Properties and add a property named PLAYCRICKET_API_KEY with your
 * Play-Cricket API token as the value. Then run runCapLimits().
 */

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

var SITE_ID = 672;
var SEASON = 2026;
var CAP_LIMIT = 8;

var TEAM_NAME_TO_IDS_LOOKUP = {
  '1s': 59723, '2s': 59724, '3s': 241803,
  '4s': 267647, '5s': 394397, 'Barbarians': 279276,
  'Badgers': 268144, 'Honey Badgers': 368707, 'Friendly': 320697,
};
var TEAM_IDS = Object.keys(TEAM_NAME_TO_IDS_LOOKUP).map(function (k) {
  return TEAM_NAME_TO_IDS_LOOKUP[k];
});
var TEAM_IDS_TO_NAMES_LOOKUP = Object.keys(TEAM_NAME_TO_IDS_LOOKUP).reduce(function (acc, k) {
  acc[TEAM_NAME_TO_IDS_LOOKUP[k]] = k;
  return acc;
}, {});

var MATCHES_URL = 'http://play-cricket.com/api/v2/matches.json?&site_id={site_id}&season={season}&api_token={api_key}';
var MATCH_DETAIL_URL = 'http://play-cricket.com/api/v2/match_detail.json?&match_id={match_id}&api_token={api_key}';

var NEUTRAL_RESULTS = ['C', 'A', 'D', 'CON', 'T'];
var RESULTS_SWAPPER = { L: 'W', W: 'L' };

function getApiKey_() {
  var apiKey = PropertiesService.getScriptProperties().getProperty('PLAYCRICKET_API_KEY');
  if (!apiKey) {
    throw new Error(
      'Script Property PLAYCRICKET_API_KEY is not set. Project Settings > Script Properties.'
    );
  }
  return apiKey;
}

// ---------------------------------------------------------------------------
// Generic helpers
// ---------------------------------------------------------------------------

function normaliseId_(value) {
  if (value === null || value === undefined || value === '') return null;
  return parseInt(value, 10);
}

function convertTeamIdsToInts_(teamIds) {
  if (!teamIds) return [];
  return teamIds.map(function (i) { return parseInt(i, 10); });
}

function makeApiRequest_(url) {
  var response = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  var status = response.getResponseCode();
  if (status !== 200) {
    throw new Error('ERROR (' + status + '): ' + response.getContentText());
  }
  return JSON.parse(response.getContentText());
}

function fillString_(template, params) {
  return Object.keys(params).reduce(function (str, key) {
    return str.replace('{' + key + '}', params[key]);
  }, template);
}

function addTeamNameIdAndInnings_(
  rows, teamName, teamId, oppositionName, oppositionId, inningsNumber, matchId
) {
  rows.forEach(function (row) {
    row.team_name = teamName;
    row.team_id = teamId;
    row.opposition_name = oppositionName;
    row.opposition_id = oppositionId;
    row.innings = inningsNumber;
    row.match_id = matchId;
  });
  return rows;
}

function getInitialsSurname_(name) {
  if (!name.replace(/ /g, '')) return null;
  var parts = name.split(' ');
  if (parts.length === 1) return parts[0];
  var initials = parts.slice(0, -1).map(function (p) { return p[0]; }).join('');
  return initials + ' ' + parts[parts.length - 1];
}

function countBalls_(oversString) {
  var parts = String(oversString).split('.');
  if (parts.length === 0) return null;
  if (parts.length === 1) parts.push('0');

  var overs = parts[0] !== '' ? parseInt(parts[0], 10) : 0;
  var balls = parts.length > 1 && parts[1] !== '' ? parseInt(parts[1], 10) : 0;
  return overs * 6 + balls;
}

function calculateOvers_(ballCount) {
  var overs = Math.floor(ballCount / 6);
  var balls = ballCount - overs * 6;
  return overs + '.' + balls;
}

function getResultLetter_(data, teamIds) {
  var resultLetter = data.result;
  var appliedTo = null;
  if (data.result_applied_to) {
    appliedTo = parseFloat(data.result_applied_to);
  }
  if (NEUTRAL_RESULTS.indexOf(resultLetter) !== -1) {
    return resultLetter;
  }
  if (teamIds.indexOf(appliedTo) === -1) {
    return RESULTS_SWAPPER[resultLetter];
  }
  return resultLetter;
}

function standardiseBat_(bat) {
  bat.forEach(function (row) {
    row.not_out = ['not out', 'retired not out', 'did not bat'].indexOf(row.how_out) !== -1 ? 1 : 0;
    ['runs', 'fours', 'sixes', 'balls', 'position'].forEach(function (col) {
      row[col] = parseInt(row[col] === '' ? '0' : row[col], 10);
    });
    row.initial_name = getInitialsSurname_(row.batsman_name);
  });
  return bat;
}

function standardiseBowl_(bowl) {
  bowl.forEach(function (row) {
    ['runs', 'wickets', 'maidens', 'no_balls', 'wides'].forEach(function (col) {
      row[col] = parseInt(row[col], 10);
    });
    row.initial_name = getInitialsSurname_(row.bowler_name);
    row.balls = countBalls_(row.overs);
  });
  return bowl;
}

function extractMatchTeamContext_(data) {
  var homeId = normaliseId_(data.home_team_id);
  var awayId = normaliseId_(data.away_team_id);
  var allIds = [homeId, awayId];
  var teamNameLookup = {};
  teamNameLookup[homeId] = data.home_club_name + ' - ' + data.home_team_name;
  teamNameLookup[awayId] = data.away_club_name + ' - ' + data.away_team_name;
  return { allIds: allIds, teamNameLookup: teamNameLookup };
}

// ---------------------------------------------------------------------------
// Array/aggregation helpers (no DataFrame library available)
// ---------------------------------------------------------------------------

function groupBy_(rows, keyFn) {
  var groups = new Map();
  rows.forEach(function (row) {
    var key = keyFn(row);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  });
  return groups;
}

function sum_(rows, fn) {
  return rows.reduce(function (acc, row) { return acc + fn(row); }, 0);
}

function uniqueCount_(rows, fn) {
  return new Set(rows.map(fn)).size;
}

// ---------------------------------------------------------------------------
// Matches
// ---------------------------------------------------------------------------

function getAllMatches_(season, teamIds, competitionIds, competitionTypes) {
  teamIds = convertTeamIdsToInts_(teamIds || []);
  competitionIds = competitionIds || [];
  competitionTypes = competitionTypes || [];

  var data = makeApiRequest_(fillString_(MATCHES_URL, {
    site_id: SITE_ID, season: season, api_key: getApiKey_(),
  }));

  var matches = data.matches || [];
  matches = matches.map(function (m) {
    var out = Object.assign({}, m);
    out.match_date = parseDateDMY_(m.match_date);
    out.competition_id = m.competition_id === '' ? null : parseFloat(m.competition_id);
    out.home_team_id = parseInt(m.home_team_id, 10);
    out.away_team_id = parseInt(m.away_team_id, 10);
    return out;
  });

  if (teamIds.length) {
    matches = matches.filter(function (m) {
      return teamIds.indexOf(m.home_team_id) !== -1 || teamIds.indexOf(m.away_team_id) !== -1;
    });
  }
  if (competitionIds.length) {
    matches = matches.filter(function (m) { return competitionIds.indexOf(m.competition_id) !== -1; });
  }
  if (competitionTypes.length) {
    matches = matches.filter(function (m) { return competitionTypes.indexOf(m.competition_type) !== -1; });
  }

  return matches;
}

function parseDateDMY_(dateStr) {
  if (!dateStr) return null;
  var parts = dateStr.split('/');
  return new Date(parseInt(parts[2], 10), parseInt(parts[1], 10) - 1, parseInt(parts[0], 10));
}

function getResultForMyTeam_(matchId, teamIds) {
  teamIds = convertTeamIdsToInts_(teamIds || []);
  var data = makeApiRequest_(fillString_(MATCH_DETAIL_URL, {
    match_id: matchId, api_key: getApiKey_(),
  }));
  data = data.match_details[0];
  return getResultLetter_(data, teamIds);
}

// ---------------------------------------------------------------------------
// Players involved
// ---------------------------------------------------------------------------

function getPlayersUsedInMatch_(matchId) {
  var data = makeApiRequest_(fillString_(MATCH_DETAIL_URL, {
    match_id: matchId, api_key: getApiKey_(),
  }));
  var detail = data.match_details[0];

  var homeTeam = detail.players[0].home_team.map(function (p) {
    return Object.assign({}, p, {
      team_id: normaliseId_(detail.home_team_id),
      club_id: normaliseId_(detail.home_club_id),
      match_id: matchId,
    });
  });
  var awayTeam = detail.players[1].away_team.map(function (p) {
    return Object.assign({}, p, {
      team_id: normaliseId_(detail.away_team_id),
      club_id: normaliseId_(detail.away_club_id),
      match_id: matchId,
    });
  });

  return homeTeam.concat(awayTeam);
}

function getAllPlayersInvolved_(matchIds, teamIds) {
  teamIds = teamIds || [];

  var players = [];
  matchIds.forEach(function (matchId) {
    try {
      players = players.concat(getPlayersUsedInMatch_(matchId));
    } catch (e) {
      Logger.log('Error occurred while fetching players for match ' + matchId + ': ' + e);
    }
  });

  if (!players.length) {
    throw new Error('No player data could be retrieved for the provided match IDs.');
  }

  if (teamIds.length) {
    players = players.filter(function (p) { return teamIds.indexOf(p.team_id) !== -1; });
  }

  var seen = new Set();
  players = players.filter(function (p) {
    var key = p.player_name + '|' + p.player_id + '|' + p.match_id;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return players;
}

// ---------------------------------------------------------------------------
// Individual stats
// ---------------------------------------------------------------------------

function getIndividualStats_(matchId, teamIds) {
  teamIds = teamIds || [];

  var data = makeApiRequest_(fillString_(MATCH_DETAIL_URL, {
    match_id: matchId, api_key: getApiKey_(),
  }));
  data = data.match_details[0];
  var ctx = extractMatchTeamContext_(data);
  var allIds = ctx.allIds;
  var teamNameLookup = ctx.teamNameLookup;

  var allBatting = [];
  var allBowling = [];

  var inningsNumber = 1;
  data.innings.forEach(function (innings) {
    var bat = innings.bat || [];
    if (!bat.length) return;
    var battingId = normaliseId_(innings.team_batting_id);
    var battingName = innings.team_batting_name;
    var bowlingId = battingId === allIds[0] ? allIds[1] : allIds[0];
    var bowlingName = teamNameLookup[bowlingId];

    var bowl = innings.bowl || [];
    if (!bowl.length) return;

    bowl = addTeamNameIdAndInnings_(
      bowl.map(function (r) { return Object.assign({}, r); }),
      bowlingName, bowlingId, battingName, battingId, inningsNumber, matchId
    );
    bat = addTeamNameIdAndInnings_(
      bat.map(function (r) { return Object.assign({}, r); }),
      battingName, battingId, bowlingName, bowlingId, inningsNumber, matchId
    );
    allBatting = allBatting.concat(bat);
    allBowling = allBowling.concat(bowl);
    inningsNumber += 1;
  });

  if (allBatting.length === 0) {
    return { batting: [], bowling: [] };
  }

  allBatting = standardiseBat_(allBatting);
  allBowling = standardiseBowl_(allBowling);

  if (teamIds.length) {
    allBatting = allBatting.filter(function (r) { return teamIds.indexOf(r.team_id) !== -1; });
    allBowling = allBowling.filter(function (r) { return teamIds.indexOf(r.team_id) !== -1; });
  }

  return { batting: allBatting, bowling: allBowling };
}

function getIndividualStatsFromAllGames_(matchIds, teamIds) {
  teamIds = teamIds || [];

  var batting = [];
  var bowling = [];
  matchIds.forEach(function (matchId) {
    var stats;
    try {
      stats = getIndividualStats_(matchId, []);
    } catch (e) {
      throw new Error('MATCH ID ' + matchId + ' FAILED WITH: ' + e);
    }
    batting = batting.concat(stats.batting);
    bowling = bowling.concat(stats.bowling);
  });

  bowling.forEach(function (row) {
    row.wickets = row.wickets || 0;
  });

  var fielding;
  if (teamIds.length) {
    fielding = batting.filter(function (r) { return teamIds.indexOf(r.team_id) === -1; }).map(function (r) { return Object.assign({}, r); });
    batting = batting.filter(function (r) { return teamIds.indexOf(r.team_id) !== -1; });
    bowling = bowling.filter(function (r) { return teamIds.indexOf(r.team_id) !== -1; });
  } else {
    fielding = batting.map(function (r) { return Object.assign({}, r); });
  }

  return { batting: batting, bowling: bowling, fielding: fielding };
}

// ---------------------------------------------------------------------------
// Season aggregates
// ---------------------------------------------------------------------------

function aggregateBattingStats_(batting, groupbyKeys) {
  batting = batting.filter(function (r) { return r.how_out !== 'did not bat'; });
  var groups = groupBy_(batting, function (r) { return groupbyKeys.map(function (k) { return r[k]; }).join('||'); });

  var out = [];
  groups.forEach(function (rows) {
    var base = groupbyKeys.reduce(function (acc, k) { acc[k] = rows[0][k]; return acc; }, {});
    var runsArr = rows.map(function (r) { return r.runs; });
    var notOut = sum_(rows, function (r) { return r.not_out; });
    var matchCount = uniqueCount_(rows, function (r) { return r.match_id; });
    var inningsToCount = matchCount - notOut;
    var runsTotal = sum_(rows, function (r) { return r.runs; });

    var row = Object.assign({}, base, {
      runs: runsTotal,
      top_score: Math.max.apply(null, runsArr),
      '50s': runsArr.filter(function (r) { return r >= 50 && r < 100; }).length,
      '100s': runsArr.filter(function (r) { return r >= 100; }).length,
      fours: sum_(rows, function (r) { return r.fours; }),
      sixes: sum_(rows, function (r) { return r.sixes; }),
      balls: sum_(rows, function (r) { return r.balls; }),
      not_out: notOut,
      match_id: matchCount,
      position: sum_(rows, function (r) { return r.position; }) / rows.length,
      innings_to_count: inningsToCount,
    });
    row.average = inningsToCount === 0 ? null : runsTotal / inningsToCount;
    out.push(row);
  });

  out.sort(function (a, b) {
    if (b.runs !== a.runs) return b.runs - a.runs;
    var avgA = a.average === null ? -Infinity : a.average;
    var avgB = b.average === null ? -Infinity : b.average;
    if (avgB !== avgA) return avgB - avgA;
    if (a.balls !== b.balls) return a.balls - b.balls;
    if (b.fours !== a.fours) return b.fours - a.fours;
    return b.sixes - a.sixes;
  });
  out.forEach(function (row, i) { row.rank = i + 1; });
  return out;
}

function aggregateBowlingStats_(bowling, groupbyKeys) {
  var groups = groupBy_(bowling, function (r) { return groupbyKeys.map(function (k) { return r[k]; }).join('||'); });

  var out = [];
  groups.forEach(function (rows) {
    var base = groupbyKeys.reduce(function (acc, k) { acc[k] = rows[0][k]; return acc; }, {});
    var wicketsArr = rows.map(function (r) { return r.wickets; });
    var wicketsTotal = sum_(rows, function (r) { return r.wickets; });
    var ballsTotal = sum_(rows, function (r) { return r.balls; });
    var runsTotal = sum_(rows, function (r) { return r.runs; });

    var row = Object.assign({}, base, {
      wickets: wicketsTotal,
      max_wickets: Math.max.apply(null, wicketsArr),
      '5fers': wicketsArr.filter(function (w) { return w >= 5; }).length,
      balls: ballsTotal,
      maidens: sum_(rows, function (r) { return r.maidens; }),
      runs: runsTotal,
      match_id: uniqueCount_(rows, function (r) { return r.match_id; }),
    });
    row.overs = calculateOvers_(ballsTotal);
    row.average = wicketsTotal === 0 ? null : runsTotal / wicketsTotal;
    row.sr = wicketsTotal === 0 ? null : ballsTotal / wicketsTotal;
    row.econ = ballsTotal === 0 ? null : (runsTotal / ballsTotal) * 6;
    out.push(row);
  });

  out.sort(function (a, b) {
    if (b.wickets !== a.wickets) return b.wickets - a.wickets;
    if (a.runs !== b.runs) return a.runs - b.runs;
    if (a.balls !== b.balls) return a.balls - b.balls;
    return a.match_id - b.match_id;
  });
  out.forEach(function (row, i) { row.rank = i + 1; });
  return out;
}

function aggregateFieldingStats_(fielding, groupbyKeys) {
  fielding = fielding.filter(function (r) { return r.fielder_name != null && r.fielder_name !== ''; });
  var groups = groupBy_(fielding, function (r) { return groupbyKeys.map(function (k) { return r[k]; }).join('||'); });

  var out = [];
  groups.forEach(function (rows) {
    var base = groupbyKeys.reduce(function (acc, k) { acc[k] = rows[0][k]; return acc; }, {});
    out.push(Object.assign({}, base, {
      dismissals: rows.length,
      n_games: uniqueCount_(rows, function (r) { return r.match_id; }),
    }));
  });

  out.sort(function (a, b) {
    if (b.dismissals !== a.dismissals) return b.dismissals - a.dismissals;
    return a.n_games - b.n_games;
  });
  out.forEach(function (row, i) { row.rank = i + 1; });
  return out;
}

function aggregateStats_(groupByTeam, batting, bowling, fielding) {
  var battingGroupby = ['initial_name', 'batsman_name', 'batsman_id'];
  var bowlingGroupby = ['initial_name', 'bowler_name', 'bowler_id'];
  var fieldingGroupby = ['fielder_name', 'fielder_id'];
  if (groupByTeam) {
    battingGroupby.push('team_id');
    bowlingGroupby.push('team_id');
    fieldingGroupby.push('team_id');
  }

  return {
    batting: aggregateBattingStats_(batting, battingGroupby),
    bowling: aggregateBowlingStats_(bowling, bowlingGroupby),
    fielding: aggregateFieldingStats_(fielding, fieldingGroupby),
  };
}

function getStatTotals_(matchIds, teamIds, groupByTeam) {
  teamIds = teamIds || [];
  var stats = getIndividualStatsFromAllGames_(matchIds, teamIds);
  return aggregateStats_(groupByTeam, stats.batting, stats.bowling, stats.fielding);
}

// ---------------------------------------------------------------------------
// Cap limits
// ---------------------------------------------------------------------------

/**
 * Flags players who are cup-tied out of a lower team by appearances for
 * higher teams, with their batting/bowling stats for the lowest team
 * they're still available for attached for context.
 *
 * Only teams named with the "<n>s" convention ('1s', '2s', ...) participate
 * in the hierarchy. A player is blocked from team n once their combined
 * appearances for every team numbered below n reach capLimit. Since that
 * block is monotonic, each capped player gets a single row keyed on the
 * first team they're blocked from.
 */
function checkCapLimitBreaches_(playersInvolvedByTeam, aggBatting, aggBowling, capLimit) {
  var teamLevelMatch;
  var teamLevels = playersInvolvedByTeam
    .map(function (r) {
      teamLevelMatch = /^(\d+)s$/.exec(r.team_name);
      if (!teamLevelMatch) return null;
      return Object.assign({}, r, { team_level: parseInt(teamLevelMatch[1], 10) });
    })
    .filter(function (r) { return r !== null; });

  // player_id|player_name -> { level -> count }
  var appearances = new Map();
  var playerNames = new Map();
  var levelsSet = new Set();
  teamLevels.forEach(function (r) {
    var key = r.player_id + '||' + r.player_name;
    if (!appearances.has(key)) appearances.set(key, {});
    var levelCounts = appearances.get(key);
    levelCounts[r.team_level] = (levelCounts[r.team_level] || 0) + r.count;
    playerNames.set(key, { player_id: r.player_id, player_name: r.player_name });
    levelsSet.add(r.team_level);
  });

  var levels = Array.from(levelsSet).sort(function (a, b) { return a - b; });

  var teamIdByLevel = {};
  teamLevels.forEach(function (r) {
    teamIdByLevel[r.team_level] = TEAM_NAME_TO_IDS_LOOKUP[r.team_name];
  });

  var breaches = [];
  appearances.forEach(function (levelCounts, key) {
    var player = playerNames.get(key);
    var cumulative = {};
    var running = 0;
    levels.forEach(function (level) {
      cumulative[level] = running;
      running += levelCounts[level] || 0;
    });

    var blockedLevels = levels.filter(function (level) {
      return level >= 2 && cumulative[level] >= capLimit;
    });
    if (!blockedLevels.length) return;

    var firstBlockedLevel = Math.min.apply(null, blockedLevels);
    var availableLevel = levels[levels.indexOf(firstBlockedLevel) - 1];

    breaches.push({
      player_id: player.player_id,
      player_name: player.player_name,
      blocked_team: firstBlockedLevel + 's',
      lowest_available_team: availableLevel + 's',
      available_team_id: teamIdByLevel[availableLevel],
      appearances_in_lowest_available_team: levelCounts[availableLevel] || 0,
      cumulative_appearances: cumulative[firstBlockedLevel],
      cap_limit: capLimit,
    });
  });

  breaches.forEach(function (breach) {
    var bat = aggBatting.find(function (r) {
      return r.batsman_id === breach.player_id && r.team_id === breach.available_team_id;
    });
    if (bat) {
      breach.runs = bat.runs;
      breach.average_batting = bat.average;
      breach.top_score = bat.top_score;
    }
    var bowl = aggBowling.find(function (r) {
      return r.bowler_id === breach.player_id && r.team_id === breach.available_team_id;
    });
    if (bowl) {
      breach.wickets = bowl.wickets;
      breach.average_bowling = bowl.average;
      breach.econ = bowl.econ;
    }
  });

  breaches.sort(function (a, b) {
    if (a.player_name !== b.player_name) return a.player_name < b.player_name ? -1 : 1;
    return a.blocked_team < b.blocked_team ? -1 : a.blocked_team > b.blocked_team ? 1 : 0;
  });

  return breaches;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function runCapLimits() {
  var matches = getAllMatches_(SEASON, TEAM_IDS, null, ['League']);
  var today = new Date();
  matches = matches.filter(function (m) { return m.match_date < today; });

  matches.forEach(function (m) { m.result = getResultForMyTeam_(m.id, []); });

  var matchIds = matches.map(function (m) { return m.id; });

  var playersInvolved = getAllPlayersInvolved_(matchIds, TEAM_IDS);

  var stats = getStatTotals_(matchIds, TEAM_IDS, true);
  var battingAgg = stats.batting;
  var bowlingAgg = stats.bowling;

  playersInvolved.forEach(function (p) {
    p.team_name = TEAM_IDS_TO_NAMES_LOOKUP[p.team_id];
  });

  var groups = groupBy_(playersInvolved, function (p) {
    return [p.team_id, p.team_name, p.player_id, p.player_name].join('||');
  });
  var playersInvolvedByTeam = [];
  groups.forEach(function (rows) {
    var r0 = rows[0];
    playersInvolvedByTeam.push({
      team_id: r0.team_id,
      team_name: r0.team_name,
      player_id: r0.player_id,
      player_name: r0.player_name,
      count: rows.length,
    });
  });
  playersInvolvedByTeam.sort(function (a, b) {
    if (a.team_id !== b.team_id) return a.team_id - b.team_id;
    return b.count - a.count;
  });

  battingAgg.forEach(function (r) { r.batsman_id = parseInt(r.batsman_id, 10); });
  bowlingAgg.forEach(function (r) { r.bowler_id = parseInt(r.bowler_id, 10); });

  var caps = checkCapLimitBreaches_(playersInvolvedByTeam, battingAgg, bowlingAgg, CAP_LIMIT);

  var capsSorted = caps.slice().sort(function (a, b) {
    return b.cumulative_appearances - a.cumulative_appearances;
  });

  var teams = Array.from(new Set(capsSorted.map(function (c) { return c.lowest_available_team; })))
    .sort(function (a, b) { return parseInt(a, 10) - parseInt(b, 10); });

  var lines = ['*Cap Limit Breaches*'];
  teams.forEach(function (team) {
    lines.push('\n*Limited to ' + team + '*');
    capsSorted
      .filter(function (c) { return c.lowest_available_team === team; })
      .forEach(function (row) {
        lines.push(row.player_name + ' - ' + row.cumulative_appearances + ' apps');
      });
  });
  var capsMessage = lines.join('\n');

  Logger.log(capsMessage);
  return capsMessage;
}
