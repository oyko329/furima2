document.addEventListener('DOMContentLoaded', () => {
    const itemForm = document.getElementById('item-form');
    const itemList = document.getElementById('item-list');
    
    // データをブラウザに保存（保存されない問題を解決）
    let items = JSON.parse(localStorage.getItem('furima_data')) || [];

    function renderItems() {
        itemList.innerHTML = '';
        items.forEach((item, index) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <div class="item-card">
                    <strong>${item.name}</strong> - ${item.salePrice}円<br>
                    <small>${item.purchaseSource} / ${item.category} / ${item.salePlatform}</small>
                </div>
                <button onclick="editItem(${index})">編集</button>
                <button onclick="deleteItem(${index})">削除</button>
            `;
            itemList.appendChild(li);
        });
        localStorage.setItem('furima_data', JSON.stringify(items));
    }

    itemForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const newItem = {
            name: document.getElementById('item-name').value,
            purchasePrice: document.getElementById('purchase-price').value,
            salePrice: document.getElementById('sale-price').value,
            purchaseDate: document.getElementById('purchase-date').value,
            saleDate: document.getElementById('sale-date').value,
            purchaseSource: document.getElementById('purchase-source').value,
            category: document.getElementById('category').value,
            salePlatform: document.getElementById('sale-platform').value
        };
        items.push(newItem);
        renderItems();
        itemForm.reset();
    });

    window.deleteItem = (index) => {
        items.splice(index, 1);
        renderItems();
    };

    window.editItem = (index) => {
        const item = items[index];
        const li = itemList.children[index];
        
        // 編集画面：商品名・価格は直接入力、その他は分野のタグから選択
        li.innerHTML = `
            <div class="edit-area">
                <input type="text" id="edit-name-${index}" value="${item.name}">
                <input type="number" id="edit-p-price-${index}" value="${item.purchasePrice}">
                <input type="number" id="edit-s-price-${index}" value="${item.salePrice}">
                
                <select id="edit-source-${index}">
                    <option value="店舗" ${item.purchaseSource === '店舗' ? 'selected' : ''}>店舗</option>
                    <option value="ネット" ${item.purchaseSource === 'ネット' ? 'selected' : ''}>ネット</option>
                    <option value="その他" ${item.purchaseSource === 'その他' ? 'selected' : ''}>その他</option>
                </select>

                <select id="edit-cat-${index}">
                    <option value="家電" ${item.category === '家電' ? 'selected' : ''}>家電</option>
                    <option value="衣服" ${item.category === '衣服' ? 'selected' : ''}>衣服</option>
                    <option value="雑貨" ${item.category === '雑貨' ? 'selected' : ''}>雑貨</option>
                </select>

                <select id="edit-plat-${index}">
                    <option value="メルカリ" ${item.salePlatform === 'メルカリ' ? 'selected' : ''}>メルカリ</option>
                    <option value="ラクマ" ${item.salePlatform === 'ラクマ' ? 'selected' : ''}>ラクマ</option>
                    <option value="ヤフオク" ${item.salePlatform === 'ヤフオク' ? 'selected' : ''}>ヤフオク</option>
                </select>

                <button onclick="saveEdit(${index})">保存</button>
                <button onclick="renderItems()">戻る</button>
            </div>
        `;
    };

    window.saveEdit = (index) => {
        items[index].name = document.getElementById(`edit-name-${index}`).value;
        items[index].purchasePrice = document.getElementById(`edit-p-price-${index}`).value;
        items[index].salePrice = document.getElementById(`edit-s-price-${index}`).value;
        items[index].purchaseSource = document.getElementById(`edit-source-${index}`).value;
        items[index].category = document.getElementById(`edit-cat-${index}`).value;
        items[index].salePlatform = document.getElementById(`edit-plat-${index}`).value;
        renderItems();
    };

    renderItems();
});