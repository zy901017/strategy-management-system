// 应用JavaScript功能
document.addEventListener('DOMContentLoaded', function() {
    // 自动隐藏提示消息
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // 表单验证
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // 数字格式化
    const numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value && this.step === '0.01') {
                this.value = parseFloat(this.value).toFixed(2);
            }
        });
    });
    
    // 工具提示初始化
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 确认删除
    const deleteLinks = document.querySelectorAll('a[href*="delete"]');
    deleteLinks.forEach(function(link) {
        link.addEventListener('click', function(event) {
            if (!confirm('确定要删除吗？此操作无法撤销。')) {
                event.preventDefault();
            }
        });
    });
    
    // 实时计算交易金额
    const priceInput = document.getElementById('price');
    const sharesInput = document.getElementById('shares');
    const feesInput = document.getElementById('fees');
    
    if (priceInput && sharesInput) {
        function calculateAmount() {
            const price = parseFloat(priceInput.value) || 0;
            const shares = parseInt(sharesInput.value) || 0;
            const fees = parseFloat(feesInput.value) || 0;
            const amount = price * shares;
            const netAmount = amount + fees;
            
            // 显示计算结果（如果有显示元素的话）
            const amountDisplay = document.getElementById('amount-display');
            if (amountDisplay) {
                amountDisplay.textContent = `交易金额: $${amount.toFixed(2)}, 净金额: $${netAmount.toFixed(2)}`;
            }
        }
        
        priceInput.addEventListener('input', calculateAmount);
        sharesInput.addEventListener('input', calculateAmount);
        if (feesInput) feesInput.addEventListener('input', calculateAmount);
    }
    
    // 页面加载动画
    const cards = document.querySelectorAll('.card');
    cards.forEach(function(card, index) {
        card.style.animationDelay = `${index * 0.1}s`;
    });
});

// 格式化货币显示
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// 格式化百分比显示
function formatPercentage(value) {
    return (value * 100).toFixed(1) + '%';
}

// 复制到剪贴板
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // 显示成功提示
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-success border-0';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">已复制到剪贴板</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 3000);
    });
}