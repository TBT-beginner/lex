# app.py (アイテムシステム完全版)

import random
import json
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_12345'

# (load_dataから一番下まで、以前のコードをすべてこれで置き換えてください)
def load_data():
    with open('quests.json', 'r', encoding='utf-8') as f:
        quests_data = json.load(f)
    with open('skills.json', 'r', encoding='utf-8') as f:
        skills_data = json.load(f)
    with open('word_materials.json', 'r', encoding='utf-8') as f:
        materials_data = json.load(f)
    with open('recipes.json', 'r', encoding='utf-8') as f:
        recipes_data = json.load(f)
    with open('items.json', 'r', encoding='utf-8') as f:
        items_data = json.load(f)
    return quests_data, skills_data, materials_data, recipes_data, items_data
QUESTS, SKILLS, MATERIALS, RECIPES, ITEMS = load_data()
CHARGE_PER_SPELL = 15
def init_player_status():
    session['level'] = 1
    session['exp'] = 0
    session['max_hp'] = 50
    session['learned_skills'] = []
    session['skill_points'] = 0
    session['next_level_exp'] = 100
    session['inventory'] = {}
    session['known_words'] = []
    session['mistaken_words'] = []
def set_new_question():
    quest_id = session.get('current_quest_id')
    word_info = None
    if quest_id == 'q_review':
        mistaken_words = session.get('mistaken_words', [])
        if not mistaken_words: return
        target_word = random.choice(mistaken_words)
        session['target_word'] = target_word
        for q_data in QUESTS.values():
            if target_word in q_data['words']:
                word_info = q_data['words'][target_word]
                break
    else:
        quest_words = QUESTS[quest_id]['words']
        target_word = random.choice(list(quest_words.keys()))
        session['target_word'] = target_word
        word_info = quest_words[target_word]
    if word_info:
        session['question_jp'] = word_info.get('jp')
        session['word_part'] = word_info.get('part')
@app.route('/')
def start_page():
    if 'level' not in session: init_player_status()
    result_message = session.pop('result_message', None)
    review_needed = bool(session.get('mistaken_words'))
    return render_template('start.html', result_message=result_message, quests=QUESTS, review_needed=review_needed, session=session)
@app.route('/start_quest', methods=['POST'])
def start_quest():
    quest_id = request.form.get('quest_id')
    if quest_id == 'q_review':
        mistaken_words = session.get('mistaken_words', [])
        if not mistaken_words: return redirect(url_for('start_page'))
        session['current_quest_id'] = 'q_review'
        session['player_hp'] = session.get('max_hp', 50) 
        session['monster_hp'] = 50 
        session['monster_name'] = "記憶の幻影"
        session['monster_attack'] = 5
        session['monster_image'] = "phantom.png"
    else:
        if quest_id not in QUESTS: return redirect(url_for('start_page'))
        quest_data = QUESTS[quest_id]
        session['current_quest_id'] = quest_id
        session['player_hp'] = session.get('max_hp', 50) 
        session['monster_hp'] = quest_data['monster']['hp']
        session['monster_name'] = quest_data['monster']['name']
        session['monster_attack'] = quest_data['monster']['attack']
        session['monster_image'] = quest_data['monster']['image']
    session['charge_power'] = 0
    session['message'] = f"{session['monster_name']}が現れた！"
    set_new_question()
    return redirect(url_for('battle_page'))
@app.route('/battle')
def battle_page():
    if 'player_hp' not in session or 'current_quest_id' not in session: return redirect(url_for('start_page'))
    return render_template('battle.html', session=session, RECIPES=RECIPES, ITEMS=ITEMS) # ITEMSも渡す
@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    quest_id = session.get('current_quest_id')
    user_answer = request.form['answer'].lower().strip()
    target_word = session.get('target_word')
    is_review_quest = (quest_id == 'q_review')
    word_info = None
    if is_review_quest:
        for q_data in QUESTS.values():
            if target_word in q_data['words']:
                word_info = q_data['words'][target_word]
                break
    else:
        word_info = QUESTS[quest_id]['words'][target_word]
    if not word_info: return redirect(url_for('battle_page'))
    if user_answer == target_word:
        if is_review_quest:
            mistaken_list = session.get('mistaken_words', [])
            if target_word in mistaken_list:
                mistaken_list.remove(target_word)
                session['mistaken_words'] = mistaken_list
                session.modified = True
            session['message'] = f"「{target_word}」！弱点を克服した！"
            session['monster_hp'] -= 20
        else:
            if word_info['part'] in ["名詞", "形容詞"]:
                charge_amount = CHARGE_PER_SPELL
                if 'efficient_charge' in session.get('learned_skills', []): charge_amount += 5
                session['charge_power'] += charge_amount
                session['message'] = f"「{user_answer}」！魔法力が練り上げられた！"
            elif word_info['part'] == "動詞":
                base_attack = 10
                if 'sharp_strike' in session.get('learned_skills', []): base_attack += 3
                total_damage = base_attack + session.get('charge_power', 0)
                critical_message = ""
                if 'critical_word' in session.get('learned_skills', []) and random.random() < 0.15:
                    total_damage *= 2
                    critical_message = "会心の一撃！ "
                session['monster_hp'] -= total_damage
                session['message'] = f"{critical_message}溜めた力を解放！「{user_answer}」！ {total_damage} の大ダメージ！"
                session['charge_power'] = 0
    else:
        if not is_review_quest:
            mistaken_list = session.get('mistaken_words', [])
            if target_word not in mistaken_list: mistaken_list.append(target_word)
            session['mistaken_words'] = mistaken_list
            session.modified = True
        if 'resilient_focus' in session.get('learned_skills', []):
            session['charge_power'] = session.get('charge_power', 0) // 2
            session['message'] = f"呪文が暴発！しかし集中を保ち、チャージが半分残った！"
        else:
            session['charge_power'] = 0
            session['message'] = f"呪文が暴発！チャージも失った！"
        session['player_hp'] -= session.get('monster_attack', 10)
        session['message'] += f" 反撃を受け {session.get('monster_attack', 10)} のダメージ！"
    if session['monster_hp'] <= 0:
        if is_review_quest:
            if not session.get('mistaken_words'):
                session['result_message'] = "全ての弱点を克服した！素晴らしい！"
            else:
                session['result_message'] = "記憶の幻影を打ち破った！"
        else:
            quest_data = QUESTS[quest_id]
            exp_reward = quest_data['exp_reward']
            session['exp'] += exp_reward
            loot_table = quest_data.get('loot_table', [])
            loot_message = ""
            if loot_table:
                looted_item_id = random.choice(loot_table)
                inventory = session.get('inventory', {})
                inventory[looted_item_id] = inventory.get(looted_item_id, 0) + 1
                session['inventory'] = inventory
                loot_message = f" [{MATERIALS[looted_item_id]['name']}]の欠片を手に入れた！"
            item_loot_message = ""
            item_loot_table = quest_data.get('item_loot', [])
            for item_info in item_loot_table:
                if random.random() < item_info['chance']:
                    item_id = item_info['id']
                    inventory = session.get('inventory', {})
                    inventory[item_id] = inventory.get(item_id, 0) + 1
                    session['inventory'] = inventory
                    item_loot_message += f" [{ITEMS[item_id]['name']}]を見つけた！"
            level_up_message = ""
            if session.get('exp', 0) >= session.get('next_level_exp', 100):
                session['level'] += 1
                session['max_hp'] += 5
                session['skill_points'] += 1
                session['exp'] -= session.get('next_level_exp', 100)
                session['next_level_exp'] = session.get('level') * 100
                level_up_message = " レベルアップ！"
            session['result_message'] = f"クエスト成功！{exp_reward}EXP獲得！{loot_message}{item_loot_message}{level_up_message}"
        return redirect(url_for('start_page'))
    elif session['player_hp'] <= 0:
        session['result_message'] = "クエスト失敗..."
        return redirect(url_for('start_page'))
    else:
        set_new_question()
        return redirect(url_for('battle_page'))
@app.route('/reset')
def reset_game():
    session.clear()
    return redirect(url_for('start_page'))
@app.route('/skills')
def skills_page():
    return render_template('skills.html', skills=SKILLS, session=session)
@app.route('/learn_skill', methods=['POST'])
def learn_skill():
    skill_id = request.form.get('skill_id')
    if skill_id in SKILLS and session.get('skill_points', 0) >= SKILLS[skill_id]['cost']:
        if skill_id in session.get('learned_skills', []):
            session['result_message'] = "そのスキルは既に習得済みです。"
        else:
            prereq = SKILLS[skill_id].get('prerequisite')
            if prereq and prereq not in session.get('learned_skills', []):
                session['result_message'] = f"前提スキル「{SKILLS[prereq]['name']}」を先に習得してください。"
            else:
                session['skill_points'] -= SKILLS[skill_id]['cost']
                session.setdefault('learned_skills', []).append(skill_id)
                session.modified = True
                session['result_message'] = f"スキル「{SKILLS[skill_id]['name']}」を習得した！"
    else:
        session['result_message'] = "スキルポイントが足りません。"
    return redirect(url_for('skills_page'))
@app.route('/workshop')
def workshop_page():
    return render_template('workshop.html', materials=MATERIALS, recipes=RECIPES, items=ITEMS, session=session)
@app.route('/forge_word', methods=['POST'])
def forge_word():
    recipe_id = request.form.get('recipe_id')
    if recipe_id in RECIPES:
        recipe = RECIPES[recipe_id]
        inventory = session.get('inventory', {})
        can_forge = True
        for material, required_count in recipe['materials'].items():
            if inventory.get(material, 0) < required_count:
                can_forge = False
                break
        if can_forge:
            for material, required_count in recipe['materials'].items():
                inventory[material] -= required_count
            session.setdefault('known_words', []).append(recipe_id)
            session['inventory'] = inventory
            session.modified = True
            session['result_message'] = f"単語「{recipe['name']}」のフォージに成功した！"
        else:
            session['result_message'] = "素材が足りません。"
    return redirect(url_for('workshop_page'))
@app.route('/cast_spell', methods=['POST'])
def cast_spell():
    spell_id = request.form.get('spell_id')
    if spell_id in RECIPES and spell_id in session.get('known_words', []):
        spell_data = RECIPES[spell_id]['spell']
        cost = spell_data['cost']
        if session.get('charge_power', 0) >= cost:
            session['charge_power'] -= cost
            effect = spell_data['effect']
            power = spell_data['power']
            if effect == 'damage':
                session['monster_hp'] -= power
                session['message'] = f"魔導書を開き「{spell_data['name']}」を詠唱！敵に {power} のダメージ！"
            elif effect == 'heal':
                session['player_hp'] += power
                if session['player_hp'] > session.get('max_hp', 50):
                    session['player_hp'] = session.get('max_hp', 50)
                session['message'] = f"「{spell_data['name']}」を詠唱！HPが {power} 回復した！"
            if session['monster_hp'] <= 0:
                quest_id = session.get('current_quest_id')
                session['result_message'] = f"クエスト成功！"
                return redirect(url_for('start_page'))
        else:
            session['message'] = "チャージパワーが足りず、詠唱に失敗した！"
    return redirect(url_for('battle_page'))
@app.route('/use_item', methods=['POST'])
def use_item():
    item_id = request.form.get('item_id')
    inventory = session.get('inventory', {})
    if item_id in inventory and inventory.get(item_id, 0) > 0:
        inventory[item_id] -= 1
        session['inventory'] = inventory
        item_data = ITEMS[item_id]
        effect = item_data['effect']
        power = item_data['power']
        if effect == 'heal_hp':
            session['player_hp'] += power
            if session['player_hp'] > session.get('max_hp', 50):
                session['player_hp'] = session.get('max_hp', 50)
            session['message'] = f"「{item_data['name']}」を使った！HPが {power} 回復！"
        elif effect == 'gain_charge':
            session['charge_power'] += power
            session['message'] = f"「{item_data['name']}」を使った！チャージが {power} 上昇！"
        session.modified = True
    else:
        session['message'] = "そのアイテムは持っていない！"
    return redirect(url_for('battle_page'))

if __name__ == '__main__':
    app.run(debug=True)