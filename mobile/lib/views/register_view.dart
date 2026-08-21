import 'package:flutter/material.dart';

import 'package:dio/dio.dart';

class RegisterView extends StatefulWidget {
  const RegisterView({super.key});

  @override
  State<RegisterView> createState() => _RegisterViewState();
}

class _RegisterViewState extends State<RegisterView> {
  int _selectedRoleIndex = 0;
  bool _agreedToTerms = false;
  bool _isLoading = false;
  
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();

  Future<void> _register() async {
    if (!_agreedToTerms) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please agree to the Terms of Service.')));
      return;
    }
    if (_passwordController.text != _confirmController.text) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Passwords do not match!')));
      return;
    }

    setState(() => _isLoading = true);
    try {
      final dio = Dio();
      final response = await dio.post(
        'http://localhost:5000/api/v1/auth/local/register',
        data: {
          'email': _emailController.text.trim(),
          'password': _passwordController.text.trim(),
          'fullName': _nameController.text.trim(),
          'roleId': _selectedRoleIndex + 1, // Basic mapping (0->1, 1->2...)
        },
      );

      if (response.statusCode == 200 && mounted) {
        Navigator.pushReplacementNamed(context, '/land_submission');
      }
    } on DioException catch (e) {
      if (mounted) {
        final message = e.response?.data?.toString() ?? e.message ?? 'Registration failed';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $message'), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.toString()}'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Widget _buildRoleButton(String title, int index) {
    final isSelected = _selectedRoleIndex == index;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _selectedRoleIndex = index),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFF1A1A2E) : Colors.transparent,
            borderRadius: BorderRadius.circular(32),
            boxShadow: isSelected ? [BoxShadow(color: Colors.black.withOpacity(0.15), blurRadius: 12, offset: const Offset(0, 4))] : [],
          ),
          alignment: Alignment.center,
          child: Text(
            title,
            style: TextStyle(
              color: isSelected ? Colors.white : const Color(0xFF47464C),
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTextField(String hint, TextEditingController controller, {bool isPassword = false}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF6F2F4),
        borderRadius: BorderRadius.circular(24),
      ),
      child: TextField(
        controller: controller,
        obscureText: isPassword,
        style: const TextStyle(fontSize: 18),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: const TextStyle(color: Color(0xFF78767D)),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFE5E1E3), // surface-variant
      body: SafeArea(
        child: Column(
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 20, 24),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back, color: Color(0xFF00000B)),
                    onPressed: () => Navigator.pop(context),
                    style: IconButton.styleFrom(backgroundColor: Colors.white, elevation: 1),
                  ),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'Create Your\nAccount',
                      style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, height: 1.2, color: Color(0xFF00000B)),
                    ),
                  ),
                ],
              ),
            ),
            
            Expanded(
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.only(topLeft: Radius.circular(32), topRight: Radius.circular(32)),
                ),
                child: ListView(
                  physics: const BouncingScrollPhysics(),
                  children: [
                    // Segmented Control
                    Container(
                      padding: const EdgeInsets.all(4),
                      margin: const EdgeInsets.only(bottom:24),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF1EDEF),
                        borderRadius: BorderRadius.circular(32),
                      ),
                      child: Row(
                        children: [
                          _buildRoleButton('Client', 0),
                          _buildRoleButton('Architect', 1),
                          _buildRoleButton('Contractor', 2),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Inputs
                    _buildTextField('Full Name', _nameController),
                    _buildTextField('Email Address', _emailController),
                    _buildTextField('Password', _passwordController, isPassword: true),
                    
                    // Strength Indicator
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 8),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(child: Container(height: 6, decoration: BoxDecoration(color: const Color(0xFF6D4CA6), borderRadius: BorderRadius.circular(4)))),
                              const SizedBox(width: 6),
                              Expanded(child: Container(height: 6, decoration: BoxDecoration(color: const Color(0xFF6D4CA6), borderRadius: BorderRadius.circular(4)))),
                              const SizedBox(width: 6),
                              Expanded(child: Container(height: 6, decoration: BoxDecoration(color: const Color(0xFFE5E1E3), borderRadius: BorderRadius.circular(4)))),
                              const SizedBox(width: 6),
                              Expanded(child: Container(height: 6, decoration: BoxDecoration(color: const Color(0xFFE5E1E3), borderRadius: BorderRadius.circular(4)))),
                            ],
                          ),
                          const SizedBox(height: 8),
                          const Text('Medium Strength', style: TextStyle(fontSize: 13, color: Color(0xFF78767D), fontWeight: FontWeight.w500)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),

                    _buildTextField('Confirm Password', _confirmController, isPassword: true),
                    
                    // Terms
                    const SizedBox(height: 16),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Checkbox(
                          value: _agreedToTerms,
                          activeColor: const Color(0xFF6D4CA6),
                          onChanged: (val) => setState(() => _agreedToTerms = val ?? false),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
                        ),
                        const Expanded(
                          child: Padding(
                            padding: EdgeInsets.only(top: 8.0),
                            child: Text.rich(
                              TextSpan(
                                text: 'I agree to the ',
                                style: TextStyle(color: Color(0xFF47464C), fontSize: 14),
                                children: [
                                  TextSpan(text: 'Terms of Service', style: TextStyle(color: Color(0xFF6D4CA6), fontWeight: FontWeight.bold)),
                                  TextSpan(text: ' and acknowledge the '),
                                  TextSpan(text: 'Privacy Policy', style: TextStyle(color: Color(0xFF6D4CA6), fontWeight: FontWeight.bold)),
                                  TextSpan(text: '.'),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 32),

                    // Submit
                    SizedBox(
                      height: 64,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _register, // Submit logic here
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF1A1A2E),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
                          elevation: 8,
                          shadowColor: const Color(0xFF1A1A2E).withOpacity(0.3),
                        ),
                        child: _isLoading 
                          ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                          : const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text('Create Account', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white)),
                                SizedBox(width: 8),
                                Icon(Icons.arrow_forward, color: Colors.white),
                              ],
                            ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Text('Already have an account? ', style: TextStyle(color: Color(0xFF78767D))),
                        GestureDetector(
                          onTap: () => Navigator.pushReplacementNamed(context, '/login'),
                          child: const Text('Log in', style: TextStyle(color: Color(0xFF00000B), fontWeight: FontWeight.bold)),
                        )
                      ],
                    ),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}