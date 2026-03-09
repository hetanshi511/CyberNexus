def calculate_security_score(missing_headers: list, cookie_issues: list, csp_issues: list, hsts_issues: list) -> tuple[int, str]:
    """
    Calculates a security score out of 100 based on a weighted grading model.
    Returns (score, grade).
    """
    score = 100
    
    # Establish weights for core headers
    weights = {
        "Strict-Transport-Security": 20,
        "Content-Security-Policy": 20,
        "X-Frame-Options": 15,
        "X-Content-Type-Options": 15,
        "Referrer-Policy": 10,
        "Permissions-Policy": 10
    }
    
    missing_names = [h['name'] for h in missing_headers]
    for key, weight_penalty in weights.items():
        if key in missing_names:
            score -= weight_penalty
            
    # Apply deductions for strictly misconfigured variants
    # For CSP, we only penalize if it's NOT a Report-Only warning
    csp_active_issues = [iss for iss in csp_issues if "[Report-Only]" not in iss]
    if csp_active_issues:
        score -= min(10, len(csp_active_issues) * 5) # Partial deduction up to 10 points
        
    hsts_active_issues = [iss for iss in hsts_issues if "[Recommendation]" not in iss]
    if hsts_active_issues:
        score -= min(5, len(hsts_active_issues) * 5)
        
    # Cookies max weight is 10
    if cookie_issues:
         high_risk = len([i for i in cookie_issues if "[High]" in i])
         med_risk = len([i for i in cookie_issues if "[Medium]" in i])
         
         cookie_deduction = (high_risk * 5) + (med_risk * 2)
         score -= min(10, cookie_deduction)
    
    # Floor at 0
    if score < 0:
        score = 0
        
    # Letter Grading
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 65:
        grade = "C"
    elif score >= 50:
        grade = "D"
    else:
        grade = "F"
        
    return score, grade
