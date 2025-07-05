"""
CAPTCHA solving utilities
"""
import base64
import time
from typing import Optional
from loguru import logger

try:
    from twocaptcha import TwoCaptcha
    TWOCAPTCHA_AVAILABLE = True
except ImportError:
    TWOCAPTCHA_AVAILABLE = False

try:
    from anticaptchaofficial.recaptchav2proxyless import recaptchaV2Proxyless
    from anticaptchaofficial.imagecaptcha import imagecaptcha
    ANTICAPTCHA_AVAILABLE = True
except ImportError:
    ANTICAPTCHA_AVAILABLE = False


class CaptchaSolver:
    """
    CAPTCHA solving using various services
    """
    
    def __init__(self, config):
        self.config = config
        self.service = config.captcha_service
        self.api_key = config.captcha_api_key
        
        if not self.api_key:
            logger.warning("No CAPTCHA API key provided")
            return
        
        # Initialize service clients
        if self.service == '2captcha' and TWOCAPTCHA_AVAILABLE:
            self.solver = TwoCaptcha(self.api_key)
        elif self.service == 'anticaptcha' and ANTICAPTCHA_AVAILABLE:
            self.solver = None  # Will be initialized per request type
        else:
            logger.warning(f"CAPTCHA service '{self.service}' not available")
            self.solver = None
    
    def solve_image_captcha(self, image_path_or_url: str) -> Optional[str]:
        """Solve image-based CAPTCHA"""
        
        if not self.solver and not self.service:
            return None
        
        try:
            if self.service == '2captcha':
                result = self.solver.normal(image_path_or_url)
                return result['code']
            
            elif self.service == 'anticaptcha':
                solver = imagecaptcha()
                solver.set_verbose(1)
                solver.set_key(self.api_key)
                
                if image_path_or_url.startswith('http'):
                    # URL
                    solver.set_url(image_path_or_url)
                else:
                    # File path
                    solver.set_file(image_path_or_url)
                
                captcha_id = solver.captcha_handler()
                
                if captcha_id:
                    return solver.get_result(captcha_id)
            
        except Exception as e:
            logger.error(f"Error solving image CAPTCHA: {e}")
        
        return None
    
    def solve_recaptcha(self, page_url: str, site_key: str) -> Optional[str]:
        """Solve reCAPTCHA v2"""
        
        if not self.solver and not self.service:
            return None
        
        try:
            if self.service == '2captcha':
                result = self.solver.recaptcha(
                    sitekey=site_key,
                    url=page_url
                )
                return result['code']
            
            elif self.service == 'anticaptcha':
                solver = recaptchaV2Proxyless()
                solver.set_verbose(1)
                solver.set_key(self.api_key)
                solver.set_website_url(page_url)
                solver.set_website_key(site_key)
                
                g_response = solver.solve_and_return_solution()
                
                if g_response != 0:
                    return g_response
                else:
                    logger.error(f"reCAPTCHA solving failed: {solver.error_code}")
            
        except Exception as e:
            logger.error(f"Error solving reCAPTCHA: {e}")
        
        return None
    
    def solve_hcaptcha(self, page_url: str, site_key: str) -> Optional[str]:
        """Solve hCaptcha"""
        
        if not self.solver and not self.service:
            return None
        
        try:
            if self.service == '2captcha':
                result = self.solver.hcaptcha(
                    sitekey=site_key,
                    url=page_url
                )
                return result['code']
            
        except Exception as e:
            logger.error(f"Error solving hCaptcha: {e}")
        
        return None
    
    def get_balance(self) -> Optional[float]:
        """Get account balance"""
        
        try:
            if self.service == '2captcha' and self.solver:
                balance = self.solver.balance()
                return float(balance)
            
            elif self.service == 'anticaptcha':
                # AntiCaptcha balance check would need separate implementation
                pass
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
        
        return None