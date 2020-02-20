from odoo import api, fields, models, exceptions, _
import datetime
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.addons.terbilang import terbilang
import logging
_logger = logging.getLogger(__name__)


class uudp(models.Model):
    _name = 'uudp'
    _inherit = 'uudp'
    
    date = fields.Date(string="Project End Date", required=True, default=fields.Date.context_today, track_visibility='onchange',)
    end_date = fields.Date(string="Maximum PJB Date",  track_visibility='onchange',)
    reviewed_by = fields.Many2one(comodel_name='hr.employee',string='Reviewed by')
    budgeted_by = fields.Many2one(comodel_name='hr.employee',string='Budget Confirmed')
    approved_by = fields.Many2one(comodel_name='hr.employee',string='Approved by')
    
    justifikasi = fields.Boolean(string="Justifikasi", track_visibility="onchange")
    pr = fields.Boolean(string="PR", track_visibility="onchange")
    ssph = fields.Boolean(string="SSPH", track_visibility="onchange")
    sph = fields.Boolean(string="SPH", track_visibility="onchange")
    ba_negosiasi = fields.Boolean(string="BA Negosiasi", track_visibility="onchange")
    disposisi = fields.Boolean(string="Disposisi Direksi/GM", track_visibility="onchange")
    surat_penunjukan = fields.Boolean(string="Surat Penunjukan", track_visibility="onchange")
    po_spk = fields.Boolean(string="PO/SPK/Kontrak", track_visibility="onchange")
    baut_bast = fields.Boolean(string="BAUT & BAST", track_visibility="onchange")
    analisa_bisnis = fields.Boolean(string="Analisa Bisnis & Project Report", track_visibility="onchange")
    tanda_terima = fields.Boolean(string="Tanda Terima", track_visibility="onchange")
    invoice_tagihan = fields.Boolean(string="Invoice(Surat Tagihan)", track_visibility="onchange")
    kwitansi = fields.Boolean(string="Kwitansi", track_visibility="onchange")
    faktur_pajak = fields.Boolean(string="Faktur Pajak", track_visibility="onchange")
    bukti_transaksi = fields.Boolean(string="Bukti Transaksi", track_visibility="onchange")

    metode_pengadaan = fields.Selection([('swakelola','Swakelola'),('pelelangan','Pelelangan'),('penunjukan_langsung','Penunjukan Langsung'),('pembelian_langsung','Pembelian Langsung'),('dll_npwp','Dan lain-lain(Copy NPWP)')], string="Metode Pengadaan", required=False)
    metode_pembayaran = fields.Selection([('tunai','Tunai'),('cek','Cek'),('bilyet_giro','Bilyet Giro'),('transfer','Transfer')], string="Metode Pembayaran", required=False)
    tahapan_pembayaran = fields.Selection([('dp','DP'),('termin','Termin'),('pelunasan','Pelunasan'),('retensi','Retensi')], string="Tahapan Pembayaran", required=False)
    cara_perolehan = fields.Selection([('pembelian','Pembelian'),('sewa','Sewa'),('sewa_beli','Sewa Beli'),('sewa_guna','Sewa Guna Usaha(Leasing)')], string="Cara Perolehan", required=False)

    vendor = fields.Many2one(comodel_name='res.partner', string="Vendors")
    description_reimberse = fields.Text(string="Description")
    
    prefix_nsfp = fields.Many2one(comodel_name="prefix.nsfp",string="Prefix NSFP")
    efaktur_pajak  = fields.Many2one(comodel_name="vit.efaktur", string="Nomor Seri Faktur Pajak", required=False, )
    journal_payment = fields.Many2one('account.journal', string='Payment Journal', domain=[('type', 'in', ('bank', 'cash'))])

    @api.multi
    def button_done_finance(self):
        if self.type == 'penyelesaian':
            partner = self.ajuan_id.responsible_id.partner_id.id
            total_ajuan = 0
            now = datetime.datetime.now()
            total_ajuan = self.total_ajuan
            if self.uudp_ids:
                account_move_line = []

                total_debit = 0.0
                for ajuan in self.uudp_ids:
                    if not ajuan.coa_debit:
                        raise UserError(_('Account atas %s belum di set!')%(ajuan.description))
                    if ajuan.partner_id :
                        partner = ajuan.partner_id.id
                    tag_id = False
                    if ajuan.store_id :
                        tag_id = [(6, 0, [ajuan.store_id.account_analytic_tag_id.id])]
                    ajuan_total = ajuan.sub_total
                    #account debit
                    if ajuan.sub_total > 0.0 :
                        account_move_line.append((0, 0 ,{'account_id'       : ajuan.coa_debit.id,
                                                         'partner_id'       : partner, 
                                                         'analytic_tag_ids' : tag_id,
                                                         'name'             : ajuan.description, 
                                                         'analytic_account_id': self.department_id.analytic_account_id.id,
                                                         'debit'            : ajuan_total, 
                                                         'date_maturity'    : self.date})) #,
                    elif ajuan.sub_total < 0.0 :
                        account_move_line.append((0, 0 ,{'account_id'       : ajuan.coa_debit.id,
                                                         'partner_id'       : partner, 
                                                         'analytic_tag_ids' : tag_id,
                                                         'name'             : ajuan.description, 
                                                         'analytic_account_id': self.department_id.analytic_account_id.id,
                                                         'credit'            : -ajuan_total, 
                                                         'date_maturity'    : self.date})) #,
                    total_debit += ajuan_total    

                if round(self.sisa_penyelesaian,2) > 0.0:
                    raise AccessError(_('Sisa penyelesaian harus tetap dimasukan ke detail penyelesaian !'))


                account_move_line.append((0, 0 ,{'account_id' : self.ajuan_id.coa_debit.id, 
                                                'partner_id': partner, 
                                                'analytic_account_id':self.department_id.analytic_account_id.id,
                                                'name' : self.notes, 
                                                # 'credit' : total_ajuan, 
                                                'credit' : total_debit, 
                                                'date_maturity':self.date})) #, 

                journal_id = self.ajuan_id.pencairan_id.journal_id
                if not journal_id :
                    journal_id = self.env['account.move'].sudo().search([('ref','ilike','%'+self.ajuan_id.name+'%')],limit=1)
                    if not journal_id :
                        raise AccessError(_('Journal pencairan tidak ditemukan !'))
                    journal_id = journal_id.journal_id
                data={"journal_id":journal_id.id,
                      "ref":self.name + ' - '+ self.ajuan_id.name,
                      "date":self.date,
                      "narration" : self.notes,
                      "company_id":self.company_id.id,
                      "line_ids":account_move_line,}

                journal_entry = self.env['account.move'].create(data)
                if journal_entry:
                    journal_entry.post()
                    self.write_state_line('done')
                    self.ajuan_id.write({'selesai':True})
                    self.post_mesages_uudp('Done')
                    return self.write({'state' : 'done', 'journal_entry_id':journal_entry.id})
                else:
                    raise AccessError(_('Gagal membuat journal entry') )
                return self.write({'state' : 'done'})

        if self.type == 'reimberse':
                journal_id = self.ajuan_id.pencairan_id.journal_id
                if not journal_id :
                    journal_id = self.env['account.move'].sudo().search([('ref','ilike','%'+self.ajuan_id.name+'%')],limit=1)
                    if not journal_id :
                        raise AccessError(_('Journal pencairan tidak ditemukan !'))
                    journal_id = journal_id.journal_id
                data={"journal_id":journal_id.id,
                      "ref":self.name + ' - '+ self.ajuan_id.name,
                      "date":self.date,
                      "narration" : self.notes,
                      "company_id":self.company_id.id,
                      "line_ids":account_move_line,}

                journal_entry = self.env['account.move'].create(data)
                if journal_entry:
                    journal_entry.post()
                    self.write_state_line('done')
                    self.ajuan_id.write({'selesai':True})
                    self.post_mesages_uudp('Done')
                    return self.write({'state' : 'done', 'journal_entry_id':journal_entry.id})
                else:
                    raise AccessError(_('Gagal membuat journal entry') )
                return self.write({'state' : 'done'})

        if self.type == 'pengajuan':
                journal_id = self.ajuan_id.pencairan_id.journal_id
                if not journal_id :
                    journal_id = self.env['account.move'].sudo().search([('ref','ilike','%'+self.ajuan_id.name+'%')],limit=1)
                    if not journal_id :
                        raise AccessError(_('Journal pencairan tidak ditemukan !'))
                    journal_id = journal_id.journal_id
                data={"journal_id":journal_id.id,
                      "ref":self.name + ' - '+ self.ajuan_id.name,
                      "date":self.date,
                      "narration" : self.notes,
                      "company_id":self.company_id.id,
                      "line_ids":account_move_line,}

                journal_entry = self.env['account.move'].create(data)
                if journal_entry:
                    journal_entry.post()
                    self.write_state_line('done')
                    self.ajuan_id.write({'selesai':True})
                    self.post_mesages_uudp('Done')
                    return self.write({'state' : 'done', 'journal_entry_id':journal_entry.id})
                else:
                    raise AccessError(_('Gagal membuat journal entry') )
                return self.write({'state' : 'done'})

uudp()


class uudpDetail(models.Model):
    _name = "uudp.detail"
    _inherit = 'uudp.detail'

    tax_reimberse = fields.Many2many('account.tax','reimberse_tax','account_id','tax_id',string='Taxes')
    tax_amount = fields.Float(string="Amount Tax", compute="_calc_sub_total", store=True)
    
    @api.depends('qty','unit_price','state','tax_reimberse')
    def _calc_sub_total(self):
        for x in self:
            qty = x.qty
            price = x.unit_price
            sub_total = qty * price
            tax_reimberse = x.tax_reimberse.amount
            tax_amount = sub_total*tax_reimberse/100
            x.tax_amount = tax_amount
            x.sub_total = sub_total-tax_amount
            x.total = sub_total

uudpDetail()

class uudpPencairan(models.Model):
    _name = 'uudp.pencairan'
    _inherit = 'uudp.pencairan'

    reviewed_by = fields.Many2one(comodel_name='hr.employee',string='Reviewed by')
    budgeted_by = fields.Many2one(comodel_name='hr.employee',string='Budget Confirmed')
    approved_by = fields.Many2one(comodel_name='hr.employee',string='Approved by')

uudpPencairan()