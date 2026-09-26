import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import '../providers/intake_provider.dart';
import '../models/land_submission.dart';
import 'package:go_router/go_router.dart';
import '../core/theme/app_tokens.dart';

class IntakeView extends ConsumerStatefulWidget{
  const IntakeView({super.key});

  @override
  ConsumerState<IntakeView> createState()=>_IntakeViewState();
}

class _IntakeViewState extends ConsumerState<IntakeView>{
  final _formKey=GlobalKey<FormState>();
  final ImagePicker _picker=ImagePicker();

  Future<void> _pickImage() async{
    final XFile? image=await _picker.pickImage(source:ImageSource.gallery);
    if(image!=null){
      ref.read(intakeProvider.notifier).setPhoto(File(image.path));
    }
  }
  
  void _submit() async {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      try {
        final workflowId = await ref.read(intakeProvider.notifier).submitIntake();
        if (workflowId != null && mounted) {
          context.go('/design/$workflowId');
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Failed to generate plan: $e', style: const TextStyle(color: Colors.white)),
              backgroundColor: AppTokens.red,
            ),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context){
    final intakeState = ref.watch(intakeProvider);

    return Scaffold(
      backgroundColor: AppTokens.bg,
      appBar: AppBar(
        backgroundColor: AppTokens.bg,
        elevation: 0,
        leading: Padding(
          padding: const EdgeInsets.only(left: 16.0),
          child: IconButton(
            icon: const Icon(Icons.arrow_back, color: AppTokens.ink),
            onPressed: () => context.go('/dashboard'),
            style: IconButton.styleFrom(
              backgroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: const BorderSide(color: AppTokens.line),
              ),
            ),
          ),
        ),
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('New Project Setup', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18, color: AppTokens.ink)),
            Text('Provide your land details and requirements', style: TextStyle(fontSize: 12, color: AppTokens.inkMute)),
          ],
        ),
      ),
      body: intakeState.when(
        loading: () => const Center(child: CircularProgressIndicator(color: AppTokens.ink)),
        error: (err, stack) => Center(child: Text('Error: $err')),
        data: (data) => _buildForm(data),
      ),
    );
  }

  Widget _buildForm(LandSubmission data) {
    return Column(
      children: [
        // Progress Bar
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 24, vertical: 8),
          child: Row(
            children: [
              Expanded(child: Divider(color: AppTokens.accent, thickness: 3)),
              SizedBox(width: 4),
              Expanded(child: Divider(color: AppTokens.line, thickness: 3)),
              SizedBox(width: 4),
              Expanded(child: Divider(color: AppTokens.line, thickness: 3)),
            ],
          ),
        ),
        Expanded(
          child: Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              physics: const BouncingScrollPhysics(),
              children: [
                _buildCard(
                  title: 'Land Details',
                  icon: Icons.map,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          flex: 2,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Land size', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
                              const SizedBox(height: 8),
                              _buildTextField(
                                hint: 'e.g. 15',
                                initialValue: data.landSizePerches?.toString() ?? '15',
                                keyboardType: TextInputType.number,
                                validator: (val) {
                                  if (val == null || val.isEmpty) return 'Required';
                                  final num = double.tryParse(val);
                                  if (num != null && num < 0) return 'Cannot be negative';
                                  return null;
                                },
                                onSaved: (val) => ref.read(intakeProvider.notifier).updateField(landSizePerches: double.tryParse(val!)),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          flex: 1,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Unit', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
                              const SizedBox(height: 8),
                              Container(
                                decoration: BoxDecoration(
                                  color: const Color(0xFFF6F2F4),
                                  borderRadius: BorderRadius.circular(AppTokens.radiusField),
                                  border: Border.all(color: AppTokens.line),
                                ),
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                                child: const Text('Perches', style: TextStyle(fontSize: 14.5, color: AppTokens.ink)),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                
                _buildCard(
                  title: 'Terrain & Topography',
                  icon: Icons.terrain,
                  children: [
                    const Text('Upload Land Photo (Optional)', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
                    const SizedBox(height: 8),
                    data.landPhoto != null
                        ? _buildPhotoPreview(data.landPhoto!)
                        : _buildPhotoUploadButton(),
                    const SizedBox(height: 24),
                    const Text('Terrain Fallback Type', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
                    const SizedBox(height: 4),
                    const Text('Upload a clear land photo to help AI identify terrain characteristics. If no photo is available, choose the terrain manually.', style: TextStyle(fontSize: 11, color: AppTokens.inkMute)),
                    const SizedBox(height: 12),
                    Container(
                      decoration: BoxDecoration(
                        color: const Color(0xFFF6F2F4),
                        borderRadius: BorderRadius.circular(AppTokens.radiusField),
                        border: Border.all(color: AppTokens.line),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<String>(
                          value: data.manualTerrainType ?? 'flat',
                          isExpanded: true,
                          icon: const Icon(Icons.keyboard_arrow_down, color: AppTokens.inkMute),
                          style: const TextStyle(fontSize: 14.5, color: AppTokens.ink),
                          items: const [
                            DropdownMenuItem(value: 'hillside', child: Text('Hillside')),
                            DropdownMenuItem(value: 'coastal', child: Text('Coastal')),
                            DropdownMenuItem(value: 'flat', child: Text('Flat / Urban')),
                            DropdownMenuItem(value: 'forested', child: Text('Forested')),
                          ],
                          onChanged: (val) => ref.read(intakeProvider.notifier).updateField(manualTerrainType: val),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                _buildCard(
                  title: 'Plot Constraints (Optional)',
                  icon: Icons.straighten,
                  children: [
                    const Text('Missing dimensions will be estimated for conceptual planning.', style: TextStyle(fontSize: 11, color: AppTokens.inkMute)),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Plot Width (ft) (Optional)', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
                              const SizedBox(height: 8),
                              _buildTextField(
                                hint: 'e.g. 50',
                                initialValue: data.plotWidth?.toString(),
                                keyboardType: TextInputType.number,
                                validator: (val) {
                                  if (val != null && val.isNotEmpty) {
                                    final num = double.tryParse(val);
                                    if (num != null && num <= 0) return 'Must be positive';
                                  }
                                  return null;
                                },
                                onSaved: (val) => ref.read(intakeProvider.notifier).updateField(plotWidth: double.tryParse(val ?? '')),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('Plot Length (ft) (Optional)', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
                              const SizedBox(height: 8),
                              _buildTextField(
                                hint: 'e.g. 100',
                                initialValue: data.plotLength?.toString(),
                                keyboardType: TextInputType.number,
                                validator: (val) {
                                  if (val != null && val.isNotEmpty) {
                                    final num = double.tryParse(val);
                                    if (num != null && num <= 0) return 'Must be positive';
                                  }
                                  return null;
                                },
                                onSaved: (val) => ref.read(intakeProvider.notifier).updateField(plotLength: double.tryParse(val ?? '')),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(child: _buildStringDropdown('Road Side', ['North', 'South', 'East', 'West'], data.roadSide ?? 'south', (val) => ref.read(intakeProvider.notifier).updateField(roadSide: val))),
                        const SizedBox(width: 16),
                        Expanded(child: _buildStringDropdown('North Direction', ['North', 'South', 'East', 'West'], data.northOrientation ?? 'north', (val) => ref.read(intakeProvider.notifier).updateField(northOrientation: val))),
                      ],
                    ),
                    const SizedBox(height: 16),
                    _buildStringDropdown('Main Access / Entrance', ['North', 'South', 'East', 'West', 'Road Side'], data.entranceSide ?? 'south', (val) => ref.read(intakeProvider.notifier).updateField(entranceSide: val)),
                    const SizedBox(height: 16),
                    const Text('Plot Setbacks (Optional)', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
                    const SizedBox(height: 8),
                    _buildTextField(
                      hint: 'e.g. Front 10ft, Rear 5ft',
                      initialValue: data.plotSetbacks,
                      validator: (val) => null,
                      onSaved: (val) => ref.read(intakeProvider.notifier).updateField(plotSetbacks: val),
                    ),
                    const SizedBox(height: 16),
                    const Text('Target Completion Date (Optional)', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
                    const SizedBox(height: 8),
                    _buildDatePicker(context, data.targetCompletionDate),
                  ],
                ),
                const SizedBox(height: 24),
                
                _buildCard(
                  title: 'Design Preferences',
                  icon: Icons.grid_view_rounded,
                  children: [
                    Row(
                      children: [
                        Expanded(child: _buildDropdown('Beds', [1, 2, 3, 4, 5], data.preferredBedrooms ?? 3, (val) => ref.read(intakeProvider.notifier).updateField(preferredBedrooms: val))),
                        const SizedBox(width: 12),
                        Expanded(child: _buildDropdown('Baths', [1, 2, 3, 4], data.preferredBathrooms ?? 1, (val) => ref.read(intakeProvider.notifier).updateField(preferredBathrooms: val))),
                        const SizedBox(width: 12),
                        Expanded(child: _buildDropdown('Floors', [1, 2, 3], data.preferredFloors ?? 1, (val) => ref.read(intakeProvider.notifier).updateField(preferredFloors: val))),
                      ],
                    ),
                    const SizedBox(height: 16),
                    const Text('Architectural Style', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
                    const SizedBox(height: 8),
                    Container(
                      decoration: BoxDecoration(
                        color: const Color(0xFFF6F2F4),
                        borderRadius: BorderRadius.circular(AppTokens.radiusField),
                        border: Border.all(color: AppTokens.line),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<String>(
                          value: data.stylePreference ?? 'modern',
                          isExpanded: true,
                          icon: const Icon(Icons.keyboard_arrow_down, color: AppTokens.inkMute),
                          style: const TextStyle(fontSize: 14.5, color: AppTokens.ink),
                          items: const [
                            DropdownMenuItem(value: 'modern', child: Text('Modern Minimalist')),
                            DropdownMenuItem(value: 'traditional', child: Text('Traditional')),
                            DropdownMenuItem(value: 'contemporary', child: Text('Contemporary')),
                          ],
                          onChanged: (val) => ref.read(intakeProvider.notifier).updateField(stylePreference: val),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text('Space Priority', style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
                    const SizedBox(height: 8),
                    Container(
                      decoration: BoxDecoration(
                        color: const Color(0xFFF6F2F4),
                        borderRadius: BorderRadius.circular(AppTokens.radiusField),
                        border: Border.all(color: AppTokens.line),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<String>(
                          value: data.spacePriority ?? 'balanced',
                          isExpanded: true,
                          icon: const Icon(Icons.keyboard_arrow_down, color: AppTokens.inkMute),
                          style: const TextStyle(fontSize: 14.5, color: AppTokens.ink),
                          items: const [
                            DropdownMenuItem(value: 'balanced', child: Text('Balanced')),
                            DropdownMenuItem(value: 'maximum_rooms', child: Text('Maximum Rooms')),
                            DropdownMenuItem(value: 'spacious_living', child: Text('Spacious Living')),
                          ],
                          onChanged: (val) => ref.read(intakeProvider.notifier).updateField(spacePriority: val),
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    Wrap(
                      spacing: 8,
                      runSpacing: 12,
                      children: [
                        _buildChip('Open-plan Living / Dining', isActive: data.openPlan, onTap: () => ref.read(intakeProvider.notifier).togglePreference('openPlan')),
                        _buildChip('Master Bedroom with Attached Bathroom', isActive: data.masterEnsuite, onTap: () => ref.read(intakeProvider.notifier).togglePreference('masterEnsuite')),
                        _buildChip('Separate Dining Area', isActive: data.separateDining, onTap: () => ref.read(intakeProvider.notifier).togglePreference('separateDining')),
                        _buildChip('Home Office', isActive: data.homeOffice, onTap: () => ref.read(intakeProvider.notifier).togglePreference('homeOffice')),
                        _buildChip('Balcony', isActive: data.balcony, onTap: () => ref.read(intakeProvider.notifier).togglePreference('balcony')),
                        _buildChip('Veranda', isActive: data.veranda, onTap: () => ref.read(intakeProvider.notifier).togglePreference('veranda')),
                        _buildChip('Utility / Laundry', isActive: data.utilityLaundry, onTap: () => ref.read(intakeProvider.notifier).togglePreference('utilityLaundry')),
                        _buildChip('Parking Required', isActive: data.parkingRequired, onTap: () => ref.read(intakeProvider.notifier).togglePreference('parkingRequired')),
                        _buildChip('Accessible / Reduced-Step Layout', isActive: data.accessibility, onTap: () => ref.read(intakeProvider.notifier).togglePreference('accessibility')),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Generate AI Plan button — at the end of the form (same as web)
                _buildGenerateButton(),
                const SizedBox(height: 80),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildGenerateButton() {
    final intakeState = ref.watch(intakeProvider);
    final isSubmitting = intakeState.isLoading;

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: const LinearGradient(
          colors: [Color(0xFF18181B), Color(0xFF27272A)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x1A000000),
            blurRadius: 14,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: isSubmitting ? null : _submit,
          borderRadius: BorderRadius.circular(16),
          splashColor: Colors.white12,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 18),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: isSubmitting
                  ? const [
                      SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(color: Color(0xFF818CF8), strokeWidth: 2),
                      ),
                      SizedBox(width: 12),
                      Text(
                        'Processing Details...',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ]
                  : const [
                      Icon(Icons.auto_awesome, color: Colors.white70, size: 18),
                      SizedBox(width: 10),
                      Text(
                        'Generate AI Plan',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDropdown(String label, List<int> items, int value, void Function(int?) onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFFF6F2F4),
            borderRadius: BorderRadius.circular(AppTokens.radiusField),
            border: Border.all(color: AppTokens.line),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<int>(
              value: value,
              isExpanded: true,
              icon: const Icon(Icons.keyboard_arrow_down, color: AppTokens.inkMute, size: 20),
              style: const TextStyle(fontSize: 14.5, color: AppTokens.ink),
              items: items.map((e) => DropdownMenuItem(value: e, child: Text('$e'))).toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStringDropdown(String label, List<String> items, String value, void Function(String?) onChanged) {
    // If the selected value isn't in the list (e.g., 'road side'), default to the first valid item to prevent crash
    final lowercaseItems = items.map((e) => e.toLowerCase()).toList();
    final safeValue = lowercaseItems.contains(value.toLowerCase()) ? value.toLowerCase() : lowercaseItems.first;
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppTokens.inkSoft)),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFFF6F2F4),
            borderRadius: BorderRadius.circular(AppTokens.radiusField),
            border: Border.all(color: AppTokens.line),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: safeValue,
              isExpanded: true,
              icon: const Icon(Icons.keyboard_arrow_down, color: AppTokens.inkMute, size: 20),
              style: const TextStyle(fontSize: 14.5, color: AppTokens.ink),
              items: items.map((e) => DropdownMenuItem(value: e.toLowerCase(), child: Text(e))).toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildChip(String label, {bool isActive = false, VoidCallback? onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppTokens.radiusPill),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: isActive ? AppTokens.accentSoft : Colors.white,
          borderRadius: BorderRadius.circular(AppTokens.radiusPill),
          border: Border.all(color: isActive ? AppTokens.accent : AppTokens.line),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isActive ? AppTokens.accent : AppTokens.inkSoft,
            fontSize: 12.5,
            fontWeight: isActive ? FontWeight.w600 : FontWeight.w500,
          ),
        ),
      ),
    );
  }

  Widget _buildCard({required String title, required IconData icon, required List<Widget> children}) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppTokens.card,
        borderRadius: BorderRadius.circular(AppTokens.radiusCardSolid),
        border: Border.all(color: AppTokens.line),
        boxShadow: const [
          BoxShadow(
            color: Color(0x1F0B0B14),
            blurRadius: 26,
            offset: Offset(0, 10),
            spreadRadius: -14,
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: AppTokens.accentSoft,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: AppTokens.accent, size: 16),
              ),
              const SizedBox(width: 12),
              Text(title, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppTokens.ink)),
            ],
          ),
          const SizedBox(height: 24),
          ...children,
        ],
      ),
    );
  }

  Widget _buildTextField({
    required String hint,
    required FormFieldSetter<String> onSaved,
    required FormFieldValidator<String> validator,
    String? initialValue,
    TextInputType? keyboardType,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFF6F2F4),
        borderRadius: BorderRadius.circular(AppTokens.radiusField),
        border: Border.all(color: AppTokens.line),
      ),
      child: TextFormField(
        initialValue: initialValue,
        keyboardType: keyboardType,
        style: const TextStyle(fontSize: 14.5, color: AppTokens.ink),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: const TextStyle(color: AppTokens.inkMute, fontSize: 14.5),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        ),
        validator: validator,
        onSaved: onSaved,
      ),
    );
  }

  Widget _buildDatePicker(BuildContext context, String? currentDate) {
    return InkWell(
      onTap: () async {
        final DateTime? picked = await showDatePicker(
          context: context,
          initialDate: DateTime.now().add(const Duration(days: 1)),
          firstDate: DateTime.now(),
          lastDate: DateTime.now().add(const Duration(days: 3650)),
        );
        if (picked != null) {
          ref.read(intakeProvider.notifier).updateField(
            targetCompletionDate: "${picked.year}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}",
          );
        }
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        decoration: BoxDecoration(
          color: const Color(0xFFF6F2F4),
          borderRadius: BorderRadius.circular(AppTokens.radiusField),
          border: Border.all(color: AppTokens.line),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              currentDate ?? 'Select a future date',
              style: TextStyle(
                fontSize: 14.5,
                color: currentDate != null ? AppTokens.ink : AppTokens.inkMute,
              ),
            ),
            const Icon(Icons.calendar_today, color: AppTokens.inkMute, size: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildPhotoUploadButton() {
    return InkWell(
      onTap: _pickImage,
      borderRadius: BorderRadius.circular(AppTokens.radiusSection),
      child: Container(
        height: 120,
        width: double.infinity,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(AppTokens.radiusSection),
        ),
        child: Container(
          decoration: BoxDecoration(
            border: Border.all(color: AppTokens.line, width: 2),
            borderRadius: BorderRadius.circular(AppTokens.radiusSection),
          ),
          child: const Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.upload_rounded, color: AppTokens.inkMute, size: 32),
              SizedBox(height: 12),
              Text('Click to upload or drag and drop', 
                style: TextStyle(color: AppTokens.inkMute, fontSize: 11.5, fontWeight: FontWeight.w500),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPhotoPreview(File photo) {
    return Stack(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(AppTokens.radiusSection),
          child: kIsWeb 
              ? Image.network(photo.path, height: 160, width: double.infinity, fit: BoxFit.cover)
              : Image.file(photo, height: 160, width: double.infinity, fit: BoxFit.cover),
        ),
        Positioned(
          top: 8,
          right: 8,
          child: InkWell(
            onTap: () => ref.read(intakeProvider.notifier).clearPhoto(),
            child: CircleAvatar(
              radius: 16,
              backgroundColor: Colors.black.withValues(alpha: 0.6),
              child: const Icon(Icons.close, color: Colors.white, size: 18),
            ),
          ),
        ),
      ],
    );
  }
}