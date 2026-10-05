import 'package:flutter/material.dart';
import '../core/theme/app_tokens.dart';
import '../models/cost_summary.dart';

/// Expandable cost estimate: the total is always visible and the cost-head
/// breakdown is revealed with "Show breakdown".
class CostBreakdownCard extends StatefulWidget {
  final CostSummary? cost;
  final bool initiallyExpanded;

  const CostBreakdownCard({super.key, required this.cost, this.initiallyExpanded = false});

  @override
  State<CostBreakdownCard> createState() => _CostBreakdownCardState();
}

class _CostBreakdownCardState extends State<CostBreakdownCard> {
  late bool _expanded = widget.initiallyExpanded;

  @override
  Widget build(BuildContext context) {
    final cost = widget.cost;
    if (cost == null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: _boxDecoration(),
        child: const Text(
          'Cost estimate is not available yet.',
          style: TextStyle(color: AppTokens.textSecondary),
        ),
      );
    }

    return Container(
      width: double.infinity,
      decoration: _boxDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _summaryHeader(cost),
          AnimatedSize(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeInOut,
            alignment: Alignment.topCenter,
            child: _expanded ? _details(cost) : const SizedBox(width: double.infinity),
          ),
        ],
      ),
    );
  }

  Widget _summaryHeader(CostSummary cost) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 8, 14),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Estimated construction cost', style: TextStyle(fontSize: 12, color: AppTokens.textSecondary)),
                const SizedBox(height: 4),
                Text(
                  formatLkr(cost.totalCostLkr),
                  key: const Key('cost-total'),
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppTokens.textPrimary),
                ),
              ],
            ),
          ),
          Semantics(
            button: true,
            expanded: _expanded,
            child: TextButton(
              key: const Key('cost-breakdown-toggle'),
              onPressed: () => setState(() => _expanded = !_expanded),
              style: TextButton.styleFrom(foregroundColor: AppTokens.statusActiveText),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(_expanded ? 'Hide breakdown' : 'Show breakdown', style: const TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(width: 4),
                  Icon(_expanded ? Icons.expand_less : Icons.expand_more, size: 20),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _details(CostSummary cost) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(height: 1, color: AppTokens.line),
          const SizedBox(height: 16),
          _meta(cost),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _amountTile('MATERIAL COST', cost.materialCostLkr)),
              const SizedBox(width: 10),
              Expanded(child: _amountTile('LABOUR COST', cost.labourCostLkr)),
            ],
          ),
          const SizedBox(height: 10),
          _amountTile('TOTAL ESTIMATED COST', cost.totalCostLkr, emphasized: true),
          if (cost.breakdown.isNotEmpty) ...[
            const SizedBox(height: 20),
            const Text(
              'COST-HEAD BREAKDOWN',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: AppTokens.textPrimary),
            ),
            const SizedBox(height: 2),
            const Text(
              'Calculated from the pricing snapshot saved with this design.',
              style: TextStyle(fontSize: 12, color: AppTokens.textSecondary),
            ),
            const SizedBox(height: 10),
            Container(
              decoration: BoxDecoration(
                border: Border.all(color: AppTokens.line),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  for (var i = 0; i < cost.breakdown.length; i++) ...[
                    if (i > 0) const Divider(height: 1, color: AppTokens.line),
                    _breakdownRow(cost.breakdown[i]),
                  ],
                  _totalRow(cost.totalCostLkr),
                ],
              ),
            ),
          ],
          const SizedBox(height: 12),
          const Text(
            'Preliminary category-level estimate based on the pricing snapshot saved with this design. '
            'It is not a final quotation or itemized bill of quantities.',
            style: TextStyle(fontSize: 11, color: AppTokens.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _meta(CostSummary cost) {
    final items = <String>[
      if (cost.formulaVersion != null) 'Method: ${cost.formulaVersion}',
      if (cost.appliedAreaSqft != null) 'Area: ${formatNumber(cost.appliedAreaSqft!)} sq ft',
      if (cost.terrainType != null) 'Terrain: ${_capitalize(cost.terrainType!)}',
      if (cost.estimatedAt != null) 'Estimated: ${formatDate(cost.estimatedAt!)}',
    ];
    if (items.isEmpty) return const SizedBox.shrink();
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: items
          .map((text) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(color: AppTokens.bg, borderRadius: BorderRadius.circular(8)),
                child: Text(text, style: const TextStyle(fontSize: 12, color: AppTokens.textSecondary)),
              ))
          .toList(),
    );
  }

  Widget _amountTile(String label, double value, {bool emphasized = false}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: emphasized ? AppTokens.primarySoft : AppTokens.bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTokens.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 0.5, color: AppTokens.textSecondary)),
          const SizedBox(height: 6),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              formatLkr(value),
              style: TextStyle(
                fontSize: emphasized ? 18 : 15,
                fontWeight: FontWeight.w700,
                color: emphasized ? AppTokens.navy : AppTokens.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _breakdownRow(CostBreakdownLine line) {
    final source = [
      if (line.provider != null) line.provider!,
      if (line.sourceReference != null) line.sourceReference!,
      if (line.pricingUpdatedAt != null) 'updated ${formatDate(line.pricingUpdatedAt!)}',
    ].join(' · ');

    return Padding(
      padding: const EdgeInsets.all(12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(line.costHead, style: const TextStyle(fontWeight: FontWeight.w700, color: AppTokens.textPrimary)),
                if (line.itemName.isNotEmpty && line.itemName != line.costHead)
                  Text(line.itemName, style: const TextStyle(fontSize: 12, color: AppTokens.textSecondary)),
                const SizedBox(height: 4),
                Text(calculationBasis(line), style: const TextStyle(fontSize: 12, color: AppTokens.textPrimary)),
                if (source.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(source, style: const TextStyle(fontSize: 11, color: AppTokens.textSecondary)),
                ],
              ],
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(formatLkr(line.amountLkr), style: const TextStyle(fontWeight: FontWeight.w700, color: AppTokens.textPrimary)),
              const SizedBox(height: 2),
              Text('${line.sharePercent.toStringAsFixed(2)}%', style: const TextStyle(fontSize: 12, color: AppTokens.textSecondary)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _totalRow(double total) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: const BoxDecoration(
        color: AppTokens.primarySoft,
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(12)),
        border: Border(top: BorderSide(color: AppTokens.line)),
      ),
      child: Row(
        children: [
          const Expanded(
            child: Text('Total estimated cost', style: TextStyle(fontWeight: FontWeight.w700, color: AppTokens.navy)),
          ),
          Text(formatLkr(total), style: const TextStyle(fontWeight: FontWeight.w700, color: AppTokens.navy)),
        ],
      ),
    );
  }

  BoxDecoration _boxDecoration() => BoxDecoration(
        color: AppTokens.card,
        borderRadius: BorderRadius.circular(AppTokens.radiusContainer),
        border: Border.all(color: AppTokens.line),
      );
}

/// "LKR 2,500/sq ft × 814 sq ft" for materials (plus terrain when not 1),
/// "0.35 × material cost" for labour.
String calculationBasis(CostBreakdownLine line) {
  if (line.isLabour) {
    return '${formatNumber(line.unitCostLkr)} × material cost';
  }
  final terrain = line.terrainMultiplier != 1 ? ' × ${formatNumber(line.terrainMultiplier)} terrain' : '';
  return '${formatLkr(line.unitCostLkr)}/sq ft × ${formatNumber(line.appliedQuantity)} sq ft$terrain';
}

/// "LKR 15,054,930.23"; whole amounts have no decimals ("LKR 2,500").
String formatLkr(double value) => 'LKR ${formatNumber(value)}';

String formatNumber(double value) {
  final rounded = (value * 100).round() / 100;
  final negative = rounded < 0;
  final fixed = rounded.abs().toStringAsFixed(2);
  final parts = fixed.split('.');
  final whole = parts[0].replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',');
  final fraction = parts[1] == '00' ? '' : '.${parts[1].endsWith('0') ? parts[1].substring(0, 1) : parts[1]}';
  return '${negative ? '-' : ''}$whole$fraction';
}

String formatDate(DateTime date) {
  final local = date.toLocal();
  return '${local.month}/${local.day}/${local.year}';
}

String _capitalize(String text) => text.isEmpty ? text : '${text[0].toUpperCase()}${text.substring(1)}';
