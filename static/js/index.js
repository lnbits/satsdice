const locationPath = [
  window.location.protocol,
  '//',
  window.location.host,
  window.location.pathname
].join('')

const mapPayLink = obj => {
  obj._data = _.clone(obj)
  obj.date = Quasar.date.formatDate(new Date(obj.time), 'YYYY-MM-DD HH:mm')
  obj.amount = new Intl.NumberFormat(LOCALE).format(obj.amount)
  obj.print_url = [locationPath, 'print/', obj.id].join('')
  obj.pay_url = [locationPath, obj.id].join('')
  return obj
}

window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      chanceValue: 0,
      multiValue: 1.5,
      currencies: [],
      fiatRates: {},
      checker: null,
      payLinks: [],
      payLinksTable: {
        pagination: {
          rowsPerPage: 10
        }
      },
      formDialog: {
        show: false,
        fixedAmount: true,
        data: {
          haircut: 0,
          min_bet: 10,
          max_bet: 1000,
          currency: 'satoshis',
          comment_chars: 0
        }
      },
      qrCodeDialog: {
        show: false,
        data: null
      }
    }
  },
  filters: {
    percent(val) {
      return val + '%'
    }
  },
  computed: {
    chanceValueCalc() {
      this.chanceValue = (
        (1 / this.multiValue) * 100 -
        this.formDialog.data.haircut -
        (1 / this.multiValue) * 10
      ).toFixed(2)
      return this.chanceValue
    }
  },
  methods: {
    chanceValueTableCalc(multiplier, haircut) {
      return ((1 / multiplier) * 100 - haircut).toFixed(2)
    },
    async getPayLinks() {
      await LNbits.api
        .request(
          'GET',
          '/satsdice/api/v1/links?all_wallets=true',
          this.g.user.wallets[0].inkey
        )
        .then(response => {
          this.payLinks = response.data.map(mapPayLink)
        })
        .catch(err => {
          clearInterval(this.checker)
          LNbits.utils.notifyApiError(err)
        })
    },
    closeFormDialog() {
      this.resetFormData()
    },
    openQrCodeDialog(linkId) {
      const link = _.findWhere(this.payLinks, {id: linkId})
      if (link.currency) this.updateFiatRate(link.currency)

      this.qrCodeDialog.data = {
        id: link.id,
        amount:
          (link.min === link.max ? link.min : `${link.min} - ${link.max}`) +
          ' ' +
          (link.currency || 'sat'),
        currency: link.currency,
        comments: link.comment_chars
          ? `${link.comment_chars} characters`
          : 'no',
        webhook: link.webhook_url || 'nowhere',
        success:
          link.success_text || link.success_url
            ? 'Display message "' +
              link.success_text +
              '"' +
              (link.success_url ? ' and URL "' + link.success_url + '"' : '')
            : 'do nothing',
        lnurl: link.lnurl,
        pay_url: link.pay_url,
        print_url: link.print_url
      }
      this.qrCodeDialog.show = true
    },
    openUpdateDialog(linkId) {
      const link = _.findWhere(this.payLinks, {id: linkId})
      if (link.currency) this.updateFiatRate(link.currency)

      this.formDialog.data = _.clone(link._data)
      this.formDialog.show = true
      this.formDialog.fixedAmount =
        this.formDialog.data.min === this.formDialog.data.max
      this.multiValue = link.multiplier
    },
    sendFormData() {
      const wallet = _.findWhere(this.g.user.wallets, {
        id: this.formDialog.data.wallet
      })
      const data = _.omit(this.formDialog.data, 'wallet')
      data.min_bet = parseInt(data.min_bet)
      data.max_bet = parseInt(data.max_bet)
      data.multiplier = parseFloat(this.multiValue)
      data.haircut = parseFloat(data.haircut)
      data.chance = parseFloat(this.chanceValue)
      data.base_url = window.location.origin

      if (data.currency === 'satoshis') data.currency = null
      if (isNaN(parseInt(data.comment_chars))) data.comment_chars = 0

      if (data.id) {
        this.updatePayLink(wallet, data)
      } else {
        this.createPayLink(wallet, data)
      }
    },
    resetFormData() {
      this.formDialog = {
        show: false,
        fixedAmount: true,
        data: {
          haircut: 0,
          min_bet: 10,
          max_bet: 1000,
          currency: 'satoshis',
          comment_chars: 0
        }
      }
    },
    updatePayLink(wallet, data) {
      const values = _.omit(
        _.pick(
          data,
          'chance',
          'base_url',
          'multiplier',
          'haircut',
          'title',
          'min_bet',
          'max_bet',
          'webhook_url',
          'success_text',
          'success_url',
          'comment_chars',
          'currency'
        ),
        (value, key) =>
          (key === 'webhook_url' ||
            key === 'success_text' ||
            key === 'success_url') &&
          (value === null || value === '')
      )

      LNbits.api
        .request(
          'PUT',
          '/satsdice/api/v1/links/' + data.id,
          wallet.adminkey,
          values
        )
        .then(response => {
          this.payLinks = _.reject(this.payLinks, obj => obj.id === data.id)
          this.payLinks.push(mapPayLink(response.data))
          this.formDialog.show = false
          this.resetFormData()
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
    },
    createPayLink(wallet, data) {
      LNbits.api
        .request('POST', '/satsdice/api/v1/links', wallet.adminkey, data)
        .then(response => {
          this.payLinks.push(mapPayLink(response.data))
          this.formDialog.show = false
          this.resetFormData()
          this.getPayLinks()
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
    },
    deletePayLink(linkId) {
      const link = _.findWhere(this.payLinks, {id: linkId})

      LNbits.utils
        .confirmDialog('Are you sure you want to delete this pay link?')
        .onOk(() => {
          LNbits.api
            .request(
              'DELETE',
              '/satsdice/api/v1/links/' + linkId,
              _.findWhere(this.g.user.wallets, {id: link.wallet}).adminkey
            )
            .then(response => {
              this.payLinks = _.reject(this.payLinks, obj => obj.id === linkId)
            })
            .catch(err => {
              LNbits.utils.notifyApiError(err)
            })
        })
    },
    updateFiatRate(currency) {
      LNbits.api
        .request('GET', '/satsdice/api/v1/rate/' + currency, null)
        .then(response => {
          let rates = _.clone(this.fiatRates)
          rates[currency] = response.data.rate
          this.fiatRates = rates
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
    }
  },
  async created() {
    // CHECK SATSDICE LINKS
    await this.getPayLinks()
  }
})
