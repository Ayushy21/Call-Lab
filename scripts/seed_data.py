"""Create fictional mixed-format sources. No real customer or financial data."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.kb import ROOT, build

DATA={
'en':[
('intro','internal','hello','This is a demo AI assistant for the fictional PracticeWorks internship. This is not a real job offer. May I ask two screening questions? Your answers stay in this local session.'),
('consent','internal','consent','May I continue with the two demo screening questions? Please say yes or no.'),
('ask_python','internal','python','Have you built something using Python? Please say yes or no.'),
('ask_hours','internal','hours','How many hours per week could you spend on this demo internship?'),
('product','product','role|internship|work|product','PracticeWorks is a fictional Python internship used only for this assessment. The work includes small APIs, tests, and documentation. There is no real opening or salary offer.'),
('qualification','qualification','qualify|eligible|eligibility|requirements|qualification','For this fictional screening, a preliminary match needs a Python project and at least 20 hours per week. A human makes the final decision. No college rank or personal background is used.'),
('policy','policy','salary|pay|stipend|policy|payment','No salary, stipend, or employment terms have been supplied for this fictional role. A human must confirm them; the assistant must not invent an amount.'),
('faq','faq','remote|office|location|where','The fictional role is remote. The demo does not ask you to relocate. No real employment arrangement is being offered.'),
('objection','objection','experience|beginner|worried|fresher','For this demo, a personal Python project can count. Prior employment is not required. A human will review the project; passing these questions does not promise selection.'),
('fallback','internal','unknown','I do not have approved information for that question. I can note a request for a human to help.'),
('human','internal','human','I have noted a request for human help in this local demo. No real person has been called or connected.'),
('callback','internal','callback','I have noted a callback request in this demo. A human would need to confirm the date, time, timezone, and contact permission. No real callback is booked.'),
('goodbye','internal','stop','Understood. I will stop here. Thank you.'),
('incomplete','internal','unsure','That is fine. I will leave your availability unconfirmed. You can give a number of hours or ask for a human.'),
('conflict','internal','conflict','That differs from your earlier answer. Should I replace it with the new number of hours? Please say yes or no.'),
('invalid_hours','internal','invalid','That number seems unusual. Please give your available hours per week, between 0 and 80.'),
('qualified','internal','qualified','Your answers meet the demo screening rules. This is only a preliminary match, not a selection or job offer. A human must review your project and availability.'),
('not_qualified','internal','not qualified','Your answers do not currently meet the demo screening rules. I will leave the final decision to a human reviewer.'),
],
'ph':[
('intro','internal','hello','Magandang araw po. AI assistant ito para sa kathang-isip na Bayan Life demo. Hindi ito totoong insurance offer. Puwede po ba tayong mag-usap tungkol sa premium reminder?'),
('consent','internal','consent','Puwede po ba tayong magpatuloy sa demo? Sabihin lang po kung oo o hindi.'),
('product','product','premium|bayad|due|paalala|reminder','Sa demo account, dalawang libong piso ang premium, due sa ikalabinlima ng Oktubre, dalawang libo dalawampu at anim. Halimbawa lang ito. Sa totoong tawag, kailangan munang kumpirmahin ang pagkakakilanlan bago sabihin ang detalye ng policy.'),
('policy','policy','lapse|late|grace|penalty|coverage','Kung late ang premium, huwag munang ipagpalagay na lapsed na ang policy. Wala tayong approved grace period o lapse date sa demo. Ipapasuri po natin sa policy team ang coverage at susunod na hakbang.'),
('qualification','qualification','eligible|qualify|qualified|age','Hindi po makakapagpasya ang bot tungkol sa eligibility o approval. Sa demo, licensed adviser ang dapat mag-review ng totoong application at policy details.'),
('faq','faq','beneficiary|rider|bank referral','Ang beneficiary ang taong nakapangalan para tumanggap ng benepisyo ayon sa policy. Ang rider ay dagdag na coverage na may sariling terms. Ang bank referral ay pagpapakilala sa adviser; hindi ito garantiya ng approval.'),
('objection','objection','mahal|pambayad|budget|afford|expensive','Naiintindihan ko po kung mabigat sa budget. Puwede tayong mag-request ng tawag mula sa policy team para alamin ang puwedeng options. Hindi ako makakapangako ng discount o palugit.'),
('fallback','internal','unknown','Pasensya po, wala akong kumpirmadong impormasyon tungkol diyan. Puwede ko pong itala na gusto ninyong makausap ang policy team.'),
('human','internal','human','Sige po. Naitala ang request ninyo para sa policy team sa demo. Wala pang totoong adviser na nakakonekta.'),
('callback','internal','callback','Sige po, naitala ang callback request sa demo. Pakikumpirma sa tao ang araw, oras, at Philippine time. Hindi pa ito totoong booking.'),
('goodbye','internal','stop','Sige po, hihinto na ako. Salamat po sa oras ninyo.'),
],
'id':[
('intro','internal','hello','Selamat pagi. Saya asisten AI untuk demo pembiayaan Nusantara yang fiktif. Ini bukan tagihan sungguhan. Boleh saya lanjutkan pengingat cicilan dalam demo ini?'),
('consent','internal','consent','Boleh kita lanjutkan demo ini? Silakan jawab iya atau tidak.'),
('product','product','cicilan|angsuran|jatuh tempo|due|reminder','Dalam akun contoh, angsuran lima ratus ribu rupiah jatuh tempo tanggal lima belas Oktober dua ribu dua puluh enam. Tenor contoh adalah dua belas bulan. Dalam layanan sungguhan, identitas harus diperiksa sebelum rincian akun dibahas.'),
('policy','policy','denda|late|penalty|terlambat|waive','Besaran denda dan masa tenggang tidak tersedia dalam aturan demo. Saya tidak boleh menebak atau menjanjikan penghapusan denda. Petugas perlu memeriksa perjanjian pembiayaan Anda.'),
('qualification','qualification','eligible|qualify|syarat|persetujuan','Persetujuan pembiayaan perlu pemeriksaan oleh petugas. Bot tidak boleh menjamin persetujuan atau meminta PIN, OTP, dan kata sandi.'),
('faq','faq','dp|down payment|tenor|payment|bayar di mana','DP adalah uang muka. Tenor adalah lama pembiayaan. Untuk pembayaran sungguhan, gunakan kanal resmi pada perjanjian atau aplikasi penyedia. Demo ini tidak memiliki rekening pembayaran.'),
('objection','objection','belum bisa bayar|nggak bisa bayar|gak bisa bayar|ora iso bayar|berat|afford','Baik, saya paham cicilannya sedang terasa berat. Saya bisa mencatat permintaan bantuan petugas. Saya tidak bisa menjanjikan perubahan tenor atau penghapusan denda.'),
('fallback','internal','unknown','Maaf, informasi itu belum tersedia di aturan demo. Saya bisa mencatat permintaan agar petugas membantu.'),
('human','internal','human','Baik, permintaan bantuan petugas sudah dicatat dalam demo. Belum ada petugas sungguhan yang tersambung.'),
('callback','internal','callback','Baik, permintaan telepon ulang dicatat dalam demo. Petugas perlu memastikan tanggal, jam, dan zona waktu: WIB, WITA, atau WIT. Ini belum menjadi jadwal sungguhan.'),
('goodbye','internal','stop','Baik, saya hentikan percakapan ini. Terima kasih.'),
]}

PH_EN={
'intro':'Hello. This is an AI assistant for the fictional Bayan Life demo, not a real insurance offer. May we discuss a sample premium reminder?',
'consent':'May we continue with this demo? Please say yes or no.',
'product':'In the sample account, the premium is two thousand Philippine pesos, due on October fifteenth, twenty twenty-six. These are fictional details. A real call must verify identity before discussing a policy.',
'policy':'A late payment does not give me enough information to say that a policy has lapsed. The demo has no approved grace period or lapse date. The policy team must check coverage and next steps.',
'qualification':'The bot cannot decide eligibility or approval. An adviser must review the real application and policy details.',
'faq':'A beneficiary is the person named to receive benefits under the policy. A rider adds coverage with its own terms. A bank referral introduces you to an adviser; it does not guarantee approval.',
'objection':'I understand that the premium may be hard to afford. I can note a request for the policy team to discuss available options. I cannot promise a discount or extra time.',
'fallback':'I do not have confirmed information about that. I can note a request for the policy team to help.',
'human':'I have noted your request for the policy team in this demo. No real adviser is connected.',
'callback':'I have noted a callback request in this demo. A person must confirm the date, time, and Philippine timezone. No real callback is booked.',
'goodbye':'Understood. I will stop here. Thank you for your time.'}

def main():
    import pymupdf
    directory=ROOT/'data/sources'; directory.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for market,rows in DATA.items():
        for index,(topic,category,keywords,text) in enumerate(rows):
            # Mixed formats test the extraction code; each is an approved small section.
            ext=['txt','html','csv','pdf'][index%4] if market=='en' else 'txt'
            name=f'{market}_{topic}.{ext}'; path=directory/name
            if ext=='html':
                path.write_text('<html><nav>Buy now Home Contact</nav><main><p>'+text+'</p></main><footer>Copyright 2026</footer></html>',encoding='utf-8')
            elif ext=='csv':
                with path.open('w',encoding='utf-8',newline='') as f:
                    w=csv.writer(f); w.writerow(['approved_answer']); w.writerow([text])
            elif ext=='pdf':
                doc=pymupdf.open(); page=doc.new_page(); page.insert_textbox((40,40,550,760),text,fontsize=12)
                doc.save(path); doc.close()
            else: path.write_text(text,encoding='utf-8')
            item={'id':f'{market}_{topic}','title':topic.replace('_',' ').title(),'topic':topic,'category':category,
                  'market':market,'language':{'en':'en','ph':'tl','id':'id'}[market],'keywords':keywords,
                  'file':'sources/'+name,'version':'1.0','effective_date':'2026-09-30','approved':True,
                  'source_kind':'fictional assessment fixture','owner':'demo reviewer'}
            if market=='en' and topic=='qualification':item['rules']={'minimum_hours':20,'python_project_required':True}
            if market=='ph':
                alt=f'sources/ph_{topic}_english.txt'
                (ROOT/'data'/alt).write_text(PH_EN[topic],encoding='utf-8')
                item['english_source']=alt
            manifest.append(item)
    (directory/'duplicate.txt').write_text(DATA['en'][4][3],encoding='utf-8')
    manifest.append({**next(x for x in manifest if x['id']=='en_product'),'file':'sources/duplicate.txt','id':'duplicate'})
    (directory/'conflicting.txt').write_text('All applicants are guaranteed a paid job, with no review.',encoding='utf-8')
    manifest.append({**manifest[0],'id':'bad_policy','file':'sources/conflicting.txt','approved':False})
    (directory/'example_form.txt').write_text('Name: Example Person; Email: sample@example.invalid; Phone: +91 90000 00000\nPreferred contact: email',encoding='utf-8')
    manifest.append({**manifest[0],'id':'pii_example','topic':'form','file':'sources/example_form.txt','approved':True})
    (directory/'empty.pdf').write_bytes(b'Not a PDF')
    manifest.append({**manifest[0],'id':'broken','file':'sources/empty.pdf'})
    manifest.append({**manifest[0],'id':'missing','file':'sources/missing.txt'})
    (ROOT/'data/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Built',len(build()),'approved records')

if __name__=='__main__': main()
