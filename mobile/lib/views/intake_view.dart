import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import '../providers/intake_provider.dart';
import '../models/land_submission.dart';

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
      final success = await ref.read(intakeProvider.notifier).submitIntake();
      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Analyzing land and generating design...'), backgroundColor: Colors.green),
        );
        // Navigate to workflow status view
      }
    }
  }

  @override
  Widget build(BuildContext context){
    final intakeState=ref.watch(intakeProvider);
    final theme=Theme.of(context);

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        title: const Text('New Project', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFF3F4F6), Color(0xFFE5E7EB)],
          ),
        ),
        child: intakeState.when(
          loading: () => _buildLoadingOverlay(),
          error: (err, stack) => Center(child: Text('Error: $err')),
          data: (data) => _buildForm(data, theme),
        ),
      ),
    );
  }
 Widget _buildLoadingOverlay() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(color: Colors.indigo),
          SizedBox(height: 24),
          Text('AI is processing your requirements...', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }

   Widget _buildForm(LandSubmission data, ThemeData theme) {
    return SafeArea(
      child: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
          physics: const BouncingScrollPhysics(),
          children: [
            _buildSectionHeader('Budget & Land Size'),
            _buildCard([
              _buildTextField(
                label: 'Total Budget (LKR)',
                icon: Icons.account_balance_wallet_outlined,
                keyboardType: TextInputType.number,
                validator: (val) => val == null || val.isEmpty ? 'Required' : null,
                onSaved: (val) => ref.read(intakeProvider.notifier).updateField(budgetLkr: double.tryParse(val!)),
              ),
              const Divider(height: 30),
              _buildTextField(
                label: 'Land Size (Perches)',
                icon: Icons.landscape_outlined,
                keyboardType: TextInputType.number,
                validator: (val) => val == null || val.isEmpty ? 'Required' : null,
                onSaved: (val) => ref.read(intakeProvider.notifier).updateField(landSizePerches: double.tryParse(val!)),
              ),
            ]),
            const SizedBox(height: 24),
            _buildSectionHeader('Terrain Analysis'),
            _buildCard([
              const Text(
                'Upload a photo of your land for AI terrain analysis, or select the terrain type manually.',
                style: TextStyle(color: Colors.grey, fontSize: 13),
              ),
              const SizedBox(height: 16),
              data.landPhoto != null
                  ? _buildPhotoPreview(data.landPhoto!)
                  : _buildPhotoUploadButton(),
              if (data.landPhoto == null) ...[
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  decoration: _inputDecoration('Manual Terrain Type', Icons.terrain_outlined),
                  items: const [
                    DropdownMenuItem(value: 'hillside', child: Text('Hillside')),
                    DropdownMenuItem(value: 'coastal', child: Text('Coastal')),
                    DropdownMenuItem(value: 'flat', child: Text('Flat/Urban')),
                    DropdownMenuItem(value: 'forested', child: Text('Forested')),
                  ],
                  onChanged: (val) => ref.read(intakeProvider.notifier).updateField(manualTerrainType: val),
                  validator: (val) => (data.landPhoto == null && val == null) ? 'Required if no photo' : null,
                ),
              ]
            ]),

            const SizedBox(height: 24),
            _buildSectionHeader('Preferences'),
            _buildCard([
              DropdownButtonFormField<int>(
                decoration: _inputDecoration('Preferred Bedrooms', Icons.bed_outlined),
                items: [1, 2, 3, 4, 5].map((e) => DropdownMenuItem(value: e, child: Text('$e Bedrooms'))).toList(),
                onChanged: (val) => ref.read(intakeProvider.notifier).updateField(preferredBedrooms: val),
                validator: (val) => val == null ? 'Required' : null,
              ),
              const Divider(height: 30),
              DropdownButtonFormField<int>(
                decoration: _inputDecoration('Preferred Floors', Icons.stairs_outlined),
                items: [1, 2, 3].map((e) => DropdownMenuItem(value: e, child: Text('$e Floors'))).toList(),
                onChanged: (val) => ref.read(intakeProvider.notifier).updateField(preferredFloors: val),
                validator: (val) => val == null ? 'Required' : null,
              ),
              const Divider(height: 30),
              DropdownButtonFormField<String>(
                decoration: _inputDecoration('Architectural Style', Icons.architecture_outlined),
                items: const [
                  DropdownMenuItem(value: 'modern', child: Text('Modern')),
                  DropdownMenuItem(value: 'traditional', child: Text('Traditional')),
                  DropdownMenuItem(value: 'minimalist', child: Text('Minimalist')),
                ],
                onChanged: (val) => ref.read(intakeProvider.notifier).updateField(stylePreference: val),
              ),
            ]),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: data.isValid ? _submit : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.indigo,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 18),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                elevation: 2,
              ),
              child: const Text('Generate Design & Estimate', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12, left: 4),
      child: Text(
        title,
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Color(0xFF1F2937)),
      ),
    );
  }
  Widget _buildCard(List<Widget> children) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 10, offset: const Offset(0, 4)),
        ],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
    );
  }
  Widget _buildTextField({
    required String label,
    required IconData icon,
    required FormFieldSetter<String> onSaved,
    required FormFieldValidator<String> validator,
    TextInputType? keyboardType,
  }) {
    return TextFormField(
      keyboardType: keyboardType,
      decoration: _inputDecoration(label, icon),
      validator: validator,
      onSaved: onSaved,
    );
  }
  InputDecoration _inputDecoration(String label, IconData icon) {
    return InputDecoration(
      labelText: label,
      prefixIcon: Icon(icon, color: Colors.indigo.shade300),
      border: InputBorder.none,
      filled: true,
      fillColor: Colors.grey.shade50,
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade200)),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.indigo, width: 2)),
      errorBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.red.shade300)),
      focusedErrorBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.red.shade400, width: 2)),
    );
  }
  Widget _buildPhotoUploadButton() {
    return InkWell(
      onTap: _pickImage,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        height: 100,
        width: double.infinity,
        decoration: BoxDecoration(
          color: Colors.indigo.shade50,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.indigo.shade200, style: BorderStyle.solid),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.add_a_photo_outlined, color: Colors.indigo.shade400, size: 32),
            const SizedBox(height: 8),
            Text('Upload Land Photo', style: TextStyle(color: Colors.indigo.shade600, fontWeight: FontWeight.w500)),
          ],
        ),
      ),
    );
  }

  Widget _buildPhotoPreview(File photo) {
    return Stack(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: Image.file(photo, height: 160, width: double.infinity, fit: BoxFit.cover),
        ),
        Positioned(
          top: 8,
          right: 8,
          child: InkWell(
            onTap: () => ref.read(intakeProvider.notifier).clearPhoto(),
            child: CircleAvatar(
              radius: 16,
              backgroundColor: Colors.black.withOpacity(0.6),
              child: const Icon(Icons.close, color: Colors.white, size: 18),
            ),
          ),
        ),
      ],
    );
  }

}