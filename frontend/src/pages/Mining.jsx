import { useEffect, useState } from 'react'
import api from '../services/api'
import useApi from '../hooks/useApi'
import {
  Async,
  DriverLink,
  EmptyState,
  Panel,
  Stat,
  Tabs,
} from '../components/ui'
import { Donut, MultiScatter, PALETTE, TelemetryBar, TelemetryLine } from '../charts'
import { int, num, pct, titleCase } from '../utils/format'

// ---------------------------------------------------------------------------
// Data Mining — K-Means clustering, race-winner prediction, Apriori
// association rules and the composite performance classification.
// ---------------------------------------------------------------------------

const TABS = [
  { id: 'clustering', label: 'K-Means Clusters' },
  { id: 'prediction', label: 'Winner Prediction' },
  { id: 'association', label: 'Association Rules' },
  { id: 'classification', label: 'Classification' },
]

const CLASS_COLORS = {
  EXCELLENT: '#00d17a',
  STRONG: '#2ea8ff',
  AVERAGE: '#ffb400',
  POOR: '#e10600',
}

const DEFAULT_DRAFT = {
  clustering: { k: '', min_races: 15 },
  prediction: { train_until: '', force: false },
  association: { min_support: 0.03, min_confidence: 0.4, min_lift: 1.05, force: false },
  classification: { season: '', force: false },
}

export default function Mining() {
  const [active, setActive] = useState('clustering')
  const [draft, setDraft] = useState(DEFAULT_DRAFT)
  const [query, setQuery] = useState({ op: 'clustering', params: DEFAULT_DRAFT.clustering })

  const seasons = useApi(() => api.seasons(), [])
  const seasonList = seasons.data || []

  const setField = (key, value) =>
    setDraft((d) => ({ ...d, [active]: { ...d[active], [key]: value } }))

  const run = (op = active, force = false) => {
    const params = { ...draft[op], force }
    setQuery({ op, params })
  }

  useEffect(() => {
    setQuery({ op: active, params: draft[active] })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  const queryKey = JSON.stringify(query)
  const result = useApi(() => {
    const { op, params } = query
    if (op === 'clustering') return api.clusters({ k: params.k, min_races: params.min_races, force: params.force })
    if (op === 'prediction') return api.prediction({ train_until: params.train_until, force: params.force })
    if (op === 'association') {
      return api.associationRules({
        min_support: params.min_support,
        min_confidence: params.min_confidence,
        min_lift: params.min_lift,
        force: params.force,
      })
    }
    return api.classification({ season: params.season, force: params.force })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryKey])

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">scikit-learn · MLxtend</div>
          <h1>Data Mining Lab</h1>
          <p className="subtitle">
            Machine learning and pattern mining over real warehouse data — every
            cluster, prediction, rule and label is computed at request time, never
            hard-coded.
          </p>
        </div>
      </div>

      <Tabs tabs={TABS} active={active} onChange={setActive} />

      {/* ------------------------------------------------------- controls */}
      {active === 'clustering' && (
        <div className="toolbar">
          <div className="field">
            <label>Number of clusters</label>
            <select className="control" value={draft.clustering.k} onChange={(e) => setField('k', e.target.value)}>
              <option value="">Auto (elbow + silhouette)</option>
              {[2, 3, 4, 5, 6, 7, 8].map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </div>
          <div className="field">
            <label>Min races per driver</label>
            <input className="control" type="number" min="5" max="100" value={draft.clustering.min_races} onChange={(e) => setField('min_races', e.target.value)} />
          </div>
          <RunButton label="Run K-Means" onClick={() => run('clustering')} onForce={() => run('clustering', true)} />
        </div>
      )}

      {active === 'prediction' && (
        <div className="toolbar">
          <div className="field">
            <label>Train until season</label>
            <select className="control" value={draft.prediction.train_until} onChange={(e) => setField('train_until', e.target.value)}>
              <option value="">Auto (latest − 2)</option>
              {seasonList.map((s) => <option key={s.season} value={s.season}>{s.season}</option>)}
            </select>
          </div>
          <RunButton label="Train models" onClick={() => run('prediction')} onForce={() => run('prediction', true)} />
        </div>
      )}

      {active === 'association' && (
        <div className="toolbar">
          <div className="field">
            <label>Min support</label>
            <input className="control" type="number" step="0.005" min="0.001" max="0.5" value={draft.association.min_support} onChange={(e) => setField('min_support', e.target.value)} />
          </div>
          <div className="field">
            <label>Min confidence</label>
            <input className="control" type="number" step="0.05" min="0.05" max="1" value={draft.association.min_confidence} onChange={(e) => setField('min_confidence', e.target.value)} />
          </div>
          <div className="field">
            <label>Min lift</label>
            <input className="control" type="number" step="0.05" min="0" max="10" value={draft.association.min_lift} onChange={(e) => setField('min_lift', e.target.value)} />
          </div>
          <RunButton label="Mine rules" onClick={() => run('association')} onForce={() => run('association', true)} />
        </div>
      )}

      {active === 'classification' && (
        <div className="toolbar">
          <div className="field">
            <label>Season sample</label>
            <select className="control" value={draft.classification.season} onChange={(e) => setField('season', e.target.value)}>
              <option value="">All seasons</option>
              {seasonList.slice().reverse().map((s) => <option key={s.season} value={s.season}>{s.season}</option>)}
            </select>
          </div>
          <RunButton label="Classify" onClick={() => run('classification')} onForce={() => run('classification', true)} />
        </div>
      )}

      <div className="mt-2">
        <Async state={result} label="Running analysis…">
          {(data) => <MiningResult op={active} data={data} />}
        </Async>
      </div>
    </>
  )
}

function RunButton({ label, onClick, onForce }) {
  return (
    <>
      <div className="field">
        <label>&nbsp;</label>
        <button className="btn primary" type="button" onClick={onClick}>{label}</button>
      </div>
      <div className="field">
        <label>&nbsp;</label>
        <button className="btn" type="button" onClick={onForce} title="Ignore the in-process cache and recompute">Recompute</button>
      </div>
    </>
  )
}

function MiningResult({ op, data }) {
  if (!data) return <EmptyState />
  if (data.error) return <EmptyState message={data.error} />
  if (op === 'clustering') return <ClusteringResult data={data} />
  if (op === 'prediction') return <PredictionResult data={data} />
  if (op === 'association') return <AssociationResult data={data} />
  return <ClassificationResult data={data} />
}

// ------------------------------------------------------------- clustering
function ClusteringResult({ data }) {
  const clusters = data.clusters || []
  const scatter = data.scatter || []
  const series = clusters.map((c) => ({
    name: `Cluster ${c.cluster}`,
    data: scatter.filter((p) => p.cluster === c.cluster),
  }))
  const elbow = data.elbow_curve || []
  const silChart = elbow.map((e) => ({ k: `k=${e.k}`, silhouette: e.silhouette }))
  const featChart = (data.profile || []).map((p) => ({
    label: `C${p.cluster}`,
    ...Object.fromEntries((p.standout_features || []).map((f) => [f, p.vs_overall?.[f] ?? 0])),
  }))

  return (
    <>
      <div className="grid grid-4">
        <Stat label="Chosen K" value={int(data.k)} tone="red" foot={data.k_selection} />
        <Stat label="Silhouette" value={num(data.silhouette, 3)} tone="green" />
        <Stat label="Drivers clustered" value={int(data.sample_size)} tone="blue" foot={`min ${data.min_races} races`} />
        <Stat label="PCA variance (2D)" value={pct((data.pca_explained_variance || []).reduce((a, b) => a + b, 0), 1)} tone="amber" />
      </div>

      <div className="grid grid-2 mt-2">
        <Panel title="Elbow method" hint="within-cluster inertia vs k">
          <TelemetryLine
            data={elbow}
            x="k"
            lines={[{ key: 'inertia', name: 'Inertia', color: '#e10600' }]}
          />
        </Panel>
        <Panel title="Silhouette score" hint="higher = better separated">
          <TelemetryBar data={silChart} x="k" bars={[{ key: 'silhouette', name: 'Silhouette', color: '#00d17a' }]} />
        </Panel>
      </div>

      <Panel title="Driver clusters in PCA space" hint="principal components of 8 standardised features" className="mt-2">
        <MultiScatter series={series} x="x" y="y" xLabel="PC1" yLabel="PC2" height={380} />
        <div className="legend-inline mt-1">
          {clusters.map((c, i) => (
            <span key={c.cluster}>
              <span className="swatch" style={{ background: PALETTE[i % PALETTE.length] }} />
              Cluster {c.cluster} · {c.size} drivers
            </span>
          ))}
        </div>
      </Panel>

      <div className="grid grid-2 mt-2">
        {clusters.map((c) => (
          <Panel key={c.cluster} title={`Cluster ${c.cluster}`} hint={`${c.size} drivers · ${num(c.avg_races, 1)} avg races`}>
            <p className="tiny muted mb-1">
              Standout features vs the field:{' '}
              {(data.profile?.find((p) => p.cluster === c.cluster)?.standout_features || []).join(', ')}
            </p>
            <div className="stack">
              {c.drivers.slice(0, 8).map((d) => (
                <div className="row spread" key={d.driver_id}>
                  <DriverLink id={d.driver_id} name={d.name} code={d.code} />
                  <span className="tiny muted">
                    {num(d.points_per_race, 2)} pts/race · {d.races} races
                  </span>
                </div>
              ))}
            </div>
          </Panel>
        ))}
      </div>

      {featChart.length > 0 && (
        <Panel title="Cluster separation" hint="top distinguishing features (delta vs overall mean)" className="mt-2">
          <TelemetryBar
            data={featChart}
            x="label"
            stacked
            bars={Object.keys(featChart[0] || {})
              .filter((k) => k !== 'label')
              .map((k, i) => ({ key: k, name: titleCase(k), color: PALETTE[i % PALETTE.length] }))}
          />
        </Panel>
      )}

      <Panel title="Feature matrix" hint="centroids in original units" className="mt-2">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Cluster</th>
                {(data.features || []).map((f) => <th key={f} className="num">{f}</th>)}
              </tr>
            </thead>
            <tbody>
              {clusters.map((c) => (
                <tr key={c.cluster}>
                  <td className="corner">C{c.cluster}</td>
                  {(data.features || []).map((f) => (
                    <td key={f} className="num">{num(c.centroid?.[f], 3)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  )
}

// ------------------------------------------------------------ prediction
function PredictionResult({ data }) {
  const models = data.models || {}
  const order = ['random_forest', 'decision_tree', 'logistic_regression'].filter((m) => models[m])
  const metricRows = order.map((m) => ({ model: titleCase(m), ...models[m] }))
  const rf = models.random_forest || {}
  const cm = rf.confusion_matrix || {}
  const importance = data.feature_importances || []
  const picks = data.winner_picks || {}

  return (
    <>
      <div className="grid grid-4">
        <Stat label="Task" value="Win?" tone="red" foot="binary classification" />
        <Stat label="Train / test rows" value={`${int(data.train_size)} / ${int(data.test_size)}`} />
        <Stat label="Test winners" value={int(data.test_winners)} tone="amber" foot={`base rate ${pct(data.base_rate, 1)}`} />
        <Stat label="Top-1 hit rate" value={pct(picks.hit_rate, 1)} tone="green" foot={`${int(picks.correct)} / ${int(picks.races)} races`} />
      </div>

      <Panel title="Model evaluation" hint={data.split} className="mt-2">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Model</th>
                <th className="num">Accuracy</th>
                <th className="num">Precision</th>
                <th className="num">Recall</th>
                <th className="num">F1</th>
                <th className="num">ROC AUC</th>
              </tr>
            </thead>
            <tbody>
              {metricRows.map((r) => (
                <tr key={r.model}>
                  <td>{r.model}</td>
                  <td className="num">{pct(r.accuracy, 1)}</td>
                  <td className="num">{pct(r.precision, 1)}</td>
                  <td className="num">{pct(r.recall, 1)}</td>
                  <td className="num">{num(r.f1, 3)}</td>
                  <td className="num">{r.roc_auc === null ? '—' : num(r.roc_auc, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="tiny muted mt-1">
          Baseline: predicting &quot;never wins&quot; would score {pct(1 - (data.base_rate || 0), 1)} accuracy but
          catch zero winners — precision/recall/F1 expose that.
        </p>
      </Panel>

      <div className="grid grid-2 mt-2">
        <Panel title="Random Forest confusion matrix" hint="test seasons">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr><th></th><th className="num">Predicted no-win</th><th className="num">Predicted win</th></tr>
              </thead>
              <tbody>
                <tr><td className="corner">Actual no-win</td><td className="num">{int(cm.tn)}</td><td className="num">{int(cm.fp)}</td></tr>
                <tr><td className="corner">Actual win</td><td className="num">{int(cm.fn)}</td><td className="num">{int(cm.tp)}</td></tr>
              </tbody>
            </table>
          </div>
          <p className="tiny muted mt-1">
            TP {int(cm.tp)} · FP {int(cm.fp)} · FN {int(cm.fn)} · TN {int(cm.tn)}
          </p>
        </Panel>

        <Panel title="Feature importance" hint="Random Forest (pre-race features only)">
          <TelemetryBar
            data={[...importance].slice(0, 9).map((f) => ({ label: f.feature, importance: f.importance }))}
            x="label"
            layout="vertical"
            bars={[{ key: 'importance', name: 'Importance', color: '#2ea8ff' }]}
            height={320}
          />
        </Panel>
      </div>

      <Panel title="Winner picks on the held-out seasons" hint="highest-probability driver per race" className="mt-2">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Season</th><th className="num">Rd</th><th>Race</th>
                <th>Predicted</th><th>Actual</th><th className="num">P(win)</th><th>✓</th>
              </tr>
            </thead>
            <tbody>
              {(picks.picks || []).slice(-15).map((p) => (
                <tr key={p.race_id}>
                  <td>{p.season}</td>
                  <td className="num">{p.round}</td>
                  <td>{p.race_name}</td>
                  <td>{p.predicted_winner}</td>
                  <td>{p.actual_winner || '—'}</td>
                  <td className="num">{pct(p.probability, 1)}</td>
                  <td>{p.correct ? '✓' : '✗'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Anti-leakage policy" className="mt-2" accent={false}>
        <p className="tiny muted">{data.leakage_policy}</p>
        <p className="tiny muted mt-1">
          Features ({data.feature_count}): {(data.features || []).join(', ')}.
        </p>
      </Panel>
    </>
  )
}

// ----------------------------------------------------------- association
function AssociationResult({ data }) {
  const rules = data.rules || []
  const items = data.item_frequencies || []
  return (
    <>
      <div className="grid grid-4">
        <Stat label="Transactions" value={int(data.dataset_size)} tone="red" foot={data.transaction_definition} />
        <Stat label="Distinct items" value={int(data.item_count)} tone="blue" />
        <Stat label="Frequent itemsets" value={int(data.frequent_itemsets)} />
        <Stat label="Rules returned" value={int(data.rule_count)} tone="green" />
      </div>

      <div className="grid grid-2 mt-2">
        <Panel title="Association rules" hint="sorted by lift, then confidence">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>If …</th><th>Then …</th>
                  <th className="num">Support</th><th className="num">Conf.</th>
                  <th className="num">Lift</th><th className="num">Conv.</th>
                </tr>
              </thead>
              <tbody>
                {rules.slice(0, 30).map((r, i) => (
                  <tr key={i}>
                    <td className="nowrap">{(r.antecedents || []).join(' & ')}</td>
                    <td className="nowrap">{(r.consequents || []).join(' & ')}</td>
                    <td className="num">{pct(r.support, 1)}</td>
                    <td className="num">{pct(r.confidence, 1)}</td>
                    <td className="num">{num(r.lift, 2)}</td>
                    <td className="num">{r.conviction === null ? '—' : num(r.conviction, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Most frequent items" hint="share of all transactions">
          <TelemetryBar
            data={items.slice(0, 15).map((it) => ({ label: it.item, frequency: Number(it.frequency) * 100 }))}
            x="label"
            layout="vertical"
            bars={[{ key: 'frequency', name: '% of transactions', color: '#ffb400' }]}
            height={420}
          />
        </Panel>
      </div>

      <Panel title="Item vocabulary" className="mt-2" accent={false}>
        <div className="stack">
          {Object.entries(data.item_definitions || {}).map(([k, v]) => (
            <div key={k} className="insight-card">
              <span className="insight-cat">{k}</span>
              <p>{v}</p>
            </div>
          ))}
        </div>
      </Panel>
    </>
  )
}

// --------------------------------------------------------- classification
function ClassificationResult({ data }) {
  const dist = data.distribution || {}
  const donut = Object.entries(dist).map(([k, v]) => ({ name: k, value: v.count }))
  const bySeason = (data.by_season || []).map((s) => ({
    season: s.season,
    EXCELLENT: s.EXCELLENT,
    STRONG: s.STRONG,
    AVERAGE: s.AVERAGE,
    POOR: s.POOR,
  }))
  const drivers = data.driver_classification || []
  const samples = data.sample_rows || []
  return (
    <>
      <div className="grid grid-4">
        <Stat label="Samples scored" value={int(data.samples_scanned)} tone="red" />
        <Stat label="Excellent" value={int(dist.EXCELLENT?.count)} tone="green" foot={pct(dist.EXCELLENT?.pct, 1)} />
        <Stat label="Average" value={int(dist.AVERAGE?.count)} tone="amber" foot={pct(dist.AVERAGE?.pct, 1)} />
        <Stat label="Poor" value={int(dist.POOR?.count)} tone="blue" foot={pct(dist.POOR?.pct, 1)} />
      </div>

      <div className="grid grid-2 mt-2">
        <Panel title="Overall performance distribution" hint="documented composite score">
          <Donut data={donut} colors={CLASS_COLORS} />
          <p className="tiny muted mt-1">{data.formula}</p>
        </Panel>
        <Panel title="Classes per season" hint="recent 15 seasons, classified finishers">
          <TelemetryBar
            data={bySeason}
            x="season"
            stacked
            bars={[
              { key: 'EXCELLENT', name: 'Excellent', color: CLASS_COLORS.EXCELLENT },
              { key: 'STRONG', name: 'Strong', color: CLASS_COLORS.STRONG },
              { key: 'AVERAGE', name: 'Average', color: CLASS_COLORS.AVERAGE },
              { key: 'POOR', name: 'Poor', color: CLASS_COLORS.POOR },
            ]}
          />
        </Panel>
      </div>

      <Panel title="Driver career classification" hint={`mean score · min ${data.driver_min_races} races`} className="mt-2">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Driver</th><th className="num">Races scored</th>
                <th className="num">Avg score</th><th className="num">Excellent %</th><th>Class</th>
              </tr>
            </thead>
            <tbody>
              {drivers.slice(0, 25).map((d) => (
                <tr key={d.driver_id}>
                  <td><DriverLink id={d.driver_id} name={d.name} code={d.code} /></td>
                  <td className="num">{int(d.races_scored)}</td>
                  <td className="num">{num(d.avg_performance_score, 3)}</td>
                  <td className="num">{pct(d.excellent_pct, 1)}</td>
                  <td>
                    <span className="badge" style={{ background: CLASS_COLORS[d.class], color: '#0a0a0c' }}>
                      {d.class}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Sample classified results" hint={data.season_filter ? `season ${data.season_filter}` : 'latest rows'} className="mt-2">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Season</th><th>Race</th><th>Driver</th><th>Team</th>
                <th className="num">Grid</th><th className="num">Finish</th>
                <th className="num">Score</th><th>Class</th>
              </tr>
            </thead>
            <tbody>
              {samples.slice(-20).map((r, i) => (
                <tr key={i}>
                  <td>{r.season}</td>
                  <td>{r.race_name}</td>
                  <td>{r.driver}</td>
                  <td>{r.constructor}</td>
                  <td className="num">{r.grid ?? '—'}</td>
                  <td className="num">{r.position ?? 'DNF'}</td>
                  <td className="num">{r.performance_score === null ? '—' : num(r.performance_score, 3)}</td>
                  <td>
                    <span className="badge" style={{ background: CLASS_COLORS[r.class], color: '#0a0a0c' }}>
                      {r.class}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Thresholds" className="mt-2" accent={false}>
        <div className="legend-inline">
          {(data.thresholds || []).map((t) => (
            <span key={t.class}>
              <span className="swatch" style={{ background: CLASS_COLORS[t.class] }} />
              {t.class}: {t.min} ≤ score &lt; {t.max}
            </span>
          ))}
        </div>
      </Panel>
    </>
  )
}
