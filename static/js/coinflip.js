window.app = Vue.createApp({
  el: '#vue',
  mixins: [windowMixin],
  data() {
    return {
      activeGame: false,
      gameComplete: false,
      gameId: '',
      coinflip: {
        name: '',
        number_of_players: 0,
        buy_in: 0
      },
      coinflipHaircut: coinflipHaircut,
      coinflipMaxPlayers: coinflipMaxPlayers,
      coinflipMaxBet: coinflipMaxBet,
      coinflipGameId: coinflipGameId,
      coinflipPageId: coinflipPageId,
      coinflipWinner: coinflipWinner,
      lnaddress: '',
      qr: {
        show: false,
        payment_request: '',
        payment_hash: ''
      }
    }
  },
  methods: {
    getQueryParam(param) {
      const urlParams = new URLSearchParams(window.location.search)
      return urlParams.get(param)
    },
    async getGame() {
      const response = await LNbits.api.request(
        'GET',
        `/satsdice/api/v1/coinflip/${this.gameId}`,
        ''
      )
      if (response.data) {
        this.coinflip = response.data
        this.activeGame = true
      }
    },
    async joinGame() {
      try {
        const data = {
          game_id: this.gameId,
          page_id: this.coinflipPageId,
          ln_address: this.lnaddress
        }

        const response = await LNbits.api.request(
          'POST',
          '/satsdice/api/v1/coinflip/join/' + this.coinflipPageId,
          '',
          data
        )
        if (response.data) {
          this.qr.payment_request = response.data.payment_request
          this.qr.payment_hash = response.data.payment_hash
          this.qr.show = true
          this.websocket()
        }
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    websocket() {
      const url = new URL(window.location)
      url.protocol = url.protocol === 'https:' ? 'wss' : 'ws'
      url.pathname = `/api/v1/ws/${this.qr.payment_hash}`
      const ws = new WebSocket(url)
      ws.addEventListener('message', async ({data}) => {
        console.log(data)
        dataArr = data.split(',')
        if (dataArr[0] == 'paid') {
          this.$q.notify({
            type: 'positive',
            message: 'Invoice Paid! Waiting for more players...'
          })
          this.qr.show = false
          ws.close()
        }
        if (dataArr[0] == 'won') {
          this.qr.show = false
          this.coinflipWinner = dataArr[1]
          this.gameComplete = true
          this.$q.notify({
            type: 'positive',
            message:
              'You flipping won the coinflip!!!\n' +
              'Payment will be with you shortly'
          })
          this.confettiFireworks()
          ws.close()
        }
        if (dataArr[0] == 'lost') {
          this.$q.notify({
            type: 'negative',
            message: 'You lost! Good luck next time!'
          })
          this.qr.show = false
          this.coinflipWinner = dataArr[1]
          this.gameComplete = true
          ws.close()
        }
        if (dataArr[0] == 'refund') {
          this.$q.notify({
            type: 'negative',
            message:
              'Game was already full :( Refunding your sats (minus registration fee)'
          })
          this.qr.show = false
          this.coinflipWinner = dataArr[1]
          this.gameComplete = true
          ws.close()
        } else {
          console.log(data)
        }
      })
    },
    copyText() {
      Quasar.copyToClipboard(window.location.href).then(() => {
        Quasar.Notify.create({
          message: 'Copied coinflip link to clipboard!',
          position: 'bottom'
        })
      })
    },
    copyInvoice() {
      Quasar.copyToClipboard(this.qr.payment_request).then(() => {
        Quasar.Notify.create({
          message: 'Invoice URL copied to clipboard!',
          position: 'bottom'
        })
      })
    },
    confettiFireworks() {
      const duration = 3 * 1000
      const animationEnd = Date.now() + duration
      const defaults = {startVelocity: 30, spread: 360, ticks: 60, zIndex: 0}

      function randomInRange(min, max) {
        return Math.random() * (max - min) + min
      }

      const interval = setInterval(function () {
        const timeLeft = animationEnd - Date.now()

        if (timeLeft <= 0) {
          return clearInterval(interval)
        }

        const particleCount = 5 * (timeLeft / duration)
        // since particles fall down, start a bit higher than random
        confetti({
          ...defaults,
          particleCount,
          origin: {x: randomInRange(0.1, 0.3), y: Math.random() - 0.2}
        })
        confetti({
          ...defaults,
          particleCount,
          origin: {x: randomInRange(0.7, 0.9), y: Math.random() - 0.2}
        })
      }, 250)
    }
  },
  async mounted() {
    this.gameId = this.coinflipGameId
    if (this.gameId) {
      await this.getGame()
      if (this.coinflip.players.length > this.coinflipMaxPlayers) {
        this.gameComplete = true
      }
    }
  }
})
