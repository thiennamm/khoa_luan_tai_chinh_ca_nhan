"""Thiết kế riêng cho lịch sử expense VND trên website; không đọc MoneyData."""
CONFIG = {
    'version': 'personal-expense-v1', 'currency': 'VND',
    'target': 'current calendar month expense recorded in website',
    'timezone': 'Asia/Ho_Chi_Minh', 'minimum_months': 3, 'ml_minimum_months': 36,
    'validation_months': 6, 'lags': [1, 2, 3, 12], 'rolling_mean_months': 3,
    'alphas': [0.1, 1.0, 10.0], 'ridge_solver': 'cholesky',
    'standard_scaler': {'with_mean': True, 'with_std': True},
    'fit_intercept': True, 'clip_lower': 0,
    'tie_order': ['mean3', 'previous', 'seasonal', 'ridge_0.1', 'ridge_1', 'ridge_10'],
    'selection': 'minimum unrounded clipped validation MAE; exact ties use tie_order',
    'display_rounding': 'whole VND, ROUND_HALF_UP; never used for selection',
}

METHOD_LABELS = {
    'mean3': 'Ước tính theo trung bình 3 tháng',
    'previous': 'Ước tính theo tháng trước',
    'seasonal': 'Ước tính theo cùng tháng năm trước',
    'ridge_0.1': 'Ridge thử nghiệm · alpha 0,1',
    'ridge_1': 'Ridge thử nghiệm · alpha 1',
    'ridge_10': 'Ridge thử nghiệm · alpha 10',
}
