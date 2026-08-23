
import 'package:flutter/material.dart';
import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'package:flutter_dotenv/flutter_dotenv.dart';

class LoginView extends StatefulWidget {
  const LoginView({super.key});

  @override
  State<LoginView> createState() => _LoginViewState();
} 

class _LoginViewState extends State<LoginView> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;

  Future<void> _signInWithEmail() async {
    setState(() => _isLoading = true);
    try {
      final dio = Dio();
      final response = await dio.post(
        'http://localhost:5265/api/v1/auth/local/login',
        data: {
          'email': _emailController.text.trim(),
          'password': _passwordController.text.trim(),
        },
      );

      if (response.statusCode == 200 && mounted) {
        Navigator.pushReplacementNamed(context, '/land_submission');
      }
    } on DioException catch (e) {
      if (mounted) {
        final message = e.response?.data?.toString() ?? e.message ?? 'Login failed';
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

  Future<void> _signInWithGoogle() async{
    setState(()=>_isLoading=true);

    try{
      final GoogleSignInAccount? googleUser=await GoogleSignIn(
        clientId: dotenv.env['GOOGLE_WEB_CLIENT_ID'],
      ).signIn();

      if(googleUser==null){
        setState(()=> _isLoading=false);
        return;
      }

      final GoogleSignInAuthentication googleAuth=await googleUser.authentication;

      final OAuthCredential credential=GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );
      final UserCredential userCredential=
        await FirebaseAuth.instance.signInWithCredential(credential);

      if(userCredential.user!=null && mounted){
        Navigator.pushReplacementNamed(context, '/land_submission');
      }
    }catch(e){
      if(mounted){
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Google Sign-In failed: ${e.toString()}'),backgroundColor: Colors.red,)
        );
      }
    }finally{
      if(mounted) setState(()=> _isLoading=false);
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    const primaryColor = Color(0xFF00000B);
    const secondaryColor = Color(0xFF6D4CA6);
    const primaryContainer = Color(0xFF1A1A2E);
    const surfaceContainerLow = Color(0xFFF6F2F4);
    const inputBgColor = Color(0xFFF1F3F5);

    return Scaffold(
      backgroundColor: surfaceContainerLow,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20.0),
              child: ConstrainedBox(
                
                constraints: BoxConstraints(minHeight: constraints.maxHeight), 
                child: IntrinsicHeight(
                  child: Column(
                    children: [
                      const SizedBox(height: 48),
                      Container(
                        width: 96,
                        height: 96,
                        decoration: BoxDecoration(
                          color: const Color(0xFFEBDCFF),
                          borderRadius: BorderRadius.circular(32),
                          boxShadow: [
                            BoxShadow(
                              color: secondaryColor.withValues(alpha: 0.15),
                              blurRadius: 32,
                              offset: const Offset(0, 12),
                            ),
                          ],
                        ),
                        child: const Icon(Icons.home_rounded, size: 48, color: secondaryColor),
                      ),
                      const SizedBox(height: 24),
                      const Text(
                        'Welcome Back',
                        style: TextStyle(
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                          color: primaryColor,
                          fontFamily: 'Plus Jakarta Sans',
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Log in to continue planning your home.',
                        style: TextStyle(
                          fontSize: 16,
                          color: Color(0xFF47464C),
                          fontFamily: 'Hanken Grotesk',
                        ),
                      ),
                      const SizedBox(height: 48),

                      // Email Field
                      Container(
                        decoration: BoxDecoration(
                          color: inputBgColor,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: TextField(
                          controller: _emailController,
                          keyboardType: TextInputType.emailAddress,
                          decoration: const InputDecoration(
                            hintText: 'Email Address',
                            prefixIcon: Icon(Icons.mail_outline, color: Color(0xFF78767D)),
                            border: InputBorder.none,
                            contentPadding: EdgeInsets.symmetric(vertical: 18),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      
                      // Password Field
                      Container(
                        decoration: BoxDecoration(
                          color: inputBgColor,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: TextField(
                          controller: _passwordController,
                          obscureText: _obscurePassword,
                          decoration: InputDecoration(
                            hintText: 'Password',
                            prefixIcon: const Icon(Icons.lock_outline, color: Color(0xFF78767D)),
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscurePassword ? Icons.visibility_off : Icons.visibility,
                                color: const Color(0xFF78767D),
                              ),
                              onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                            ),
                            border: InputBorder.none,
                            contentPadding: const EdgeInsets.symmetric(vertical: 18),
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      
                      // Forgot Password
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: () => Navigator.pushNamed(context, '/register'),
                          child: const Text(
                            'Forgot password?',
                            style: TextStyle(color: secondaryColor, fontWeight: FontWeight.w600),
                          ),
                        ),
                      ),
                      const Spacer(),
                      
                      // Login Button
                      SizedBox(
                        width: double.infinity,
                        height: 56,
                        child: ElevatedButton(
                          onPressed: _isLoading ? null : _signInWithEmail,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: primaryContainer,
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                            elevation: 4,
                            shadowColor: primaryContainer.withValues(alpha: 0.4),
                          ),
                          child: _isLoading
                              ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                              : const Text('Log In', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                        ),
                      ),
                      const SizedBox(height: 24),

                      const SizedBox(height: 24),
                      const Row(
                        children: [
                          Expanded(child: Divider()),
                          Padding(
                            padding: EdgeInsets.symmetric(horizontal: 16),
                            child: Text('OR', style: TextStyle(color: Color(0xFF78767D), fontWeight: FontWeight.bold)),
                          ),
                          Expanded(child: Divider()),
                        ],
                      ),
                      const SizedBox(height: 24),
                      
                      // Google Sign-In Button
                      SizedBox(
                        width: double.infinity,
                        height: 56,
                        child: OutlinedButton.icon(
                          onPressed: _isLoading ? null : _signInWithGoogle,
                          icon: Image.network(
                            'https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Google_%22G%22_Logo.svg/512px-Google_%22G%22_Logo.svg.png',
                            height: 24,
                            errorBuilder: (context, error, stackTrace) => const Icon(Icons.g_mobiledata, size: 32),
                          ),
                          label: const Flexible(
                            child: Text(
                              'Continue with Google',
                              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFF00000B)),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          style: OutlinedButton.styleFrom(
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                            side: const BorderSide(color: Color(0xFFE5E7EB), width: 2),
                          ),
                        ),
                      ),
                                            
                      // Footer
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Text('Don\'t have an account?', style: TextStyle(color: Color(0xFF47464C))),
                          TextButton(
                            onPressed: () => Navigator.pushReplacementNamed(context, '/register'),
                            child: const Text('Sign Up', style: TextStyle(color: secondaryColor, fontWeight: FontWeight.bold)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}